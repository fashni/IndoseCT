import sys

import numpy as np
import pydicom
from pydicom.errors import InvalidDicomError
from scipy import ndimage as ndi
from skimage.measure import label, regionprops
from skimage.morphology import dilation, disk, erosion


def get_hu_imgs(scans):
  imgs = np.stack([get_hu_img(ds) for ds in scans])
  return imgs

def get_hu_img(ds):
  try:
    img = ds.pixel_array*ds.RescaleSlope + ds.RescaleIntercept
  except:
    return
  return np.array(img, dtype=np.int16)

def get_dicom(*args, **kwargs):
  try:
    dcm = pydicom.dcmread(*args, **kwargs)
  except InvalidDicomError as e:
    kwargs['force'] = True
    dcm = pydicom.dcmread(*args, **kwargs)
  if not hasattr(dcm.file_meta, 'TransferSyntaxUID'): # Assume transder syntax
    dcm.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2' # Implicit VR Endian
    # dcm.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1' # Explicit VR Little Endian
    # dcm.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1.99' # Deflated Explicit VR Little Endian
    # dcm.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.2' # 	Explicit VR Big Endian
  return dcm

def reslice(dcms, reverse=False):
  slices = []
  skipcount = 0
  for dcm in dcms:
    if hasattr(dcm, 'SliceLocation'):
      slices.append(dcm)
    else:
      skipcount += 1

  slices = sorted(slices, key=lambda s: s.SliceLocation, reverse=reverse)
  return slices, skipcount

def get_reference(file):
  ref = pydicom.dcmread(file)
  ref_data = {
    'dimension': (int(ref.Rows), int(ref.Columns)),
    'spacing': (float(ref.PixelSpacing[0]), float(ref.PixelSpacing[1]), float(ref.SliceThickness)),
    'intercept': float(ref.RescaleIntercept),
    'slope': float(ref.RescaleSlope),
    'reconst_diameter': float(ref.ReconstructionDiameter),
    'slice_pos': float(ref.SliceLocation),
    'CTDI': float(ref.CTDIvol) if 'CTDIvol' in ref else 0
  }
  patient_info = {
    'name': str(ref.PatientName) if 'PatientName' in ref else None,
    'sex': str(ref.PatientSex) if 'PatientSex' in ref else None,
    'age': str(ref.PatientAge) if 'PatientAge' in ref else None,
    'protocol': str(ref.BodyPartExamined) if 'BodyPartExamined' in ref else None,
    'date': str(ref.AcquisitionDate) if 'AcquisitionDate' in ref else None
  }
  return ref_data, patient_info

def get_img_no_table(img, threshold=-200):
  thres = img>threshold
  fill = ndi.binary_fill_holes(thres)
  labels = label(fill)

  regprops = get_regprops(labels)
  tables = np.zeros_like(labels, dtype=bool)
  for region in regprops:
    if region.centroid[0] > labels.shape[0]*7.5//10:
      tables = tables | (labels==region.label)

  tables = dilation(tables, disk(10))
  no_table = img.copy()
  no_table[tables] = -1000
  return no_table

def get_mask(img, threshold=-300, minimum_area=500, num_of_objects=5, largest_only=False, return_label=False):
  if largest_only:
    num_of_objects = 1
  thres = img>threshold
  fill = ndi.binary_fill_holes(thres)
  labels = label(fill)
  if labels.max() == 0:
    return (None, None) if return_label else None

  regprops = get_regprops(labels)
  obj_count = 0
  segments = np.zeros_like(labels, dtype=bool)
  for region in regprops:
    if region.centroid[0] < labels.shape[0]*7//10 and region.area >= minimum_area:
      segments = segments | (labels==region.label)
      obj_count += 1
    if obj_count == num_of_objects:
      break
  if obj_count == 0:
    return (None, None) if return_label else None

  labels = label(segments)
  return (segments, labels) if return_label else segments

def get_coord(grid, x):
  where = np.where(grid==x)
  list_of_coordinates = tuple(zip(where[0], where[1]))
  return list_of_coordinates

def get_regprops(mask, img=None):
  r_props = regionprops(mask.astype(int), intensity_image=img)
  r_props.sort(key=lambda reg: reg.area, reverse=True)
  return r_props

def get_dw_value(img, mask, dims, rd, is_truncated=False, largest_only=False):
  r,c = dims
  lbl = label(mask)
  roi = get_regprops(lbl, img)
  if largest_only:
    px_area = roi[0].area
    avg = roi[0].mean_intensity
  else:
    objs_area = [reg.area for reg in roi]
    objs_avg = [reg.mean_intensity for reg in roi]
    px_area = sum(objs_area)
    avg = sum(objs_avg)/len(objs_avg)
  area = px_area*(rd**2)/(r*c)
  dw = 0.1*2*np.sqrt(((avg/1000)+1)*(area/np.pi))
  if is_truncated:
    percent = truncation(mask)
    dw *= np.exp(1.14e-6 * percent**3)
  return dw

def get_center(mask):
  lbl = label(mask)
  roi = get_regprops(lbl)
  centroid = roi[0].centroid
  return tuple([int(x) for x in centroid])

def get_center_max(mask):
  lbl = label(mask)
  roi = get_regprops(lbl)
  bb = roi[0].image
  min_row, min_col, _, _ = roi[0].bbox
  bbrow, bbcol = bb.shape
  len_rows = np.array([bb[:, c].sum() for c in range(bbcol)])
  len_cols = np.array([bb[r, :].sum() for r in range(bbrow)])
  return (int(np.argmax(len_cols) + min_row), int(np.argmax(len_rows) + min_col))

def get_correction_mask(img, mask=None, lb_bone=250, lb_stissue=-250):
  if mask is None:
    mask = get_mask(img)
  corr_mask = mask.astype(int)
  corr_mask[(corr_mask==1) & (img<lb_stissue)] = 20
  corr_mask[(corr_mask==1) & (img<lb_bone)] = 40
  corr_mask[(corr_mask==1)] = 60
  return corr_mask

def get_deff_correction(correction, corr_mask, center, rd):
  r,c = corr_mask.shape
  is_lung, is_bone = correction
  col = corr_mask[center[0], :]
  row = corr_mask[:, center[1]]
  uniq_r, count_r = np.unique(np.delete(row, np.where(row==0)), return_counts=True)
  uniq_c, count_c = np.unique(np.delete(col, np.where(col==0)), return_counts=True)
  if is_lung:
    count_r[np.where(uniq_r==20)] = 0.3 * count_r[np.where(uniq_r==20)]
    count_c[np.where(uniq_c==20)] = 0.3 * count_c[np.where(uniq_c==20)]
  if is_bone:
    count_r[np.where(uniq_r==60)] = 1.8 * count_r[np.where(uniq_r==60)]
    count_c[np.where(uniq_c==60)] = 1.8 * count_c[np.where(uniq_c==60)]

  corr_len_r = sum(count_r) * (0.1*rd/r)
  corr_len_c = sum(count_c) * (0.1*rd/c)
  deff = np.sqrt(corr_len_r*corr_len_c)
  return deff, corr_len_r, corr_len_c

def get_deff_value(mask, dims, rd, method):
  lbl = label(mask)
  r,c = dims
  roi = get_regprops(lbl)
  px_area = roi[0].area
  bb = roi[0].image
  cen_row = cen_col = len_row = len_col = None
  row, col = lbl.shape
  if method == 'area':
    area = px_area*(rd**2)/(r*c)
    deff = 2*0.1*np.sqrt(area/np.pi)
  elif method == 'center':
    bb_cen_row, bb_cen_col = roi[0].local_centroid
    bb_cen_row, bb_cen_col = int(bb_cen_row), int(bb_cen_col)

    nrow1 = sum(bb[:, bb_cen_col])
    ncol1 = sum(bb[bb_cen_row, :])

    cen_row, cen_col = roi[0].centroid
    cen_row, cen_col = int(cen_row), int(cen_col)

    len_row = nrow1 * (0.1*rd/row)
    len_col = ncol1 * (0.1*rd/col)

    deff = np.sqrt(len_row*len_col)
  elif method == 'max':
    min_row, min_col, max_row, max_col = roi[0].bbox

    bbrow, bbcol = bb.shape
    len_rows = np.array([bb[:, c].sum() for c in range(bbcol)])
    len_cols = np.array([bb[r, :].sum() for r in range(bbrow)])

    len_row = np.max(len_rows) * (0.1*rd/row)
    len_col = np.max(len_cols) * (0.1*rd/col)

    cen_row = np.argmax(len_cols) + min_row
    cen_col = np.argmax(len_rows) + min_col

    deff = np.sqrt(len_row*len_col)
  else:
    deff = 0
  return deff, cen_row, cen_col, len_row, len_col

def truncation(mask):
  row, col = mask.shape
  pos = get_mask_pos(mask)
  edge_row = (pos[:,0]==0) | (pos[:,0]==row-1)
  edge_col = (pos[:,1]==0) | (pos[:,1]==col-1)
  edge_area = edge_row.sum() + edge_col.sum()
  area = len(pos)
  return (edge_area/area) * 100

def get_mask_pos(mask):
  pad = np.zeros((mask.shape[0]+2, mask.shape[1]+2))
  pad[1:mask.shape[0]+1, 1:mask.shape[1]+1] = mask
  edges = pad - erosion(pad, disk(1))
  pos = np.array(get_coord(edges, True))-1
  return pos

def windowing(img, window_width, window_level):
  img_min = window_level - (window_width//2)
  img_max = window_level + (window_width//2)
  win = img.copy()
  win[win < img_min] = img_min
  win[win > img_max] = img_max
  return win

if __name__ == "__main__":
  if len(sys.argv) != 2:
    sys.exit(-1)
  print(sys.argv[1])
  ds = get_dicom(sys.argv[1])
  ref, _ = get_reference(sys.argv[1])
  img = get_hu_img(ds)
  area, _, _, _, _ = get_deff_value(get_mask(img), ref['dimension'], ref['reconst_diameter'], 'area')
  center, _, _, _, _ = get_deff_value(get_mask(img), ref['dimension'], ref['reconst_diameter'], 'center')
  _max, _, _, _, _ = get_deff_value(get_mask(img), ref['dimension'], ref['reconst_diameter'], 'max')
  dw = get_dw_value(img, get_mask(img), ref['dimension'], ref['reconst_diameter'])
  print(f'deff area = {area: #.2f} cm')
  print(f'deff center = {center: #.2f} cm')
  print(f'deff max = {_max: #.2f} cm')
  print(f'dw = {dw: #.2f} cm')

  bone = windowing(img, 2000,400)
  brain = windowing(img, 70,35)
