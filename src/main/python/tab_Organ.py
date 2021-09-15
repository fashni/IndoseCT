import numpy as np
import scipy.io as scio
from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlTableModel
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QScrollArea, QStackedWidget,
                             QVBoxLayout, QWidget, QProgressDialog)
from scipy import interpolate

from constants import *
from image_processing import get_center, get_mask
from Plot import AxisItem, PlotDialog, ImageViewDialog


class OrganTab(QWidget):
  def __init__(self, ctx, *args, **kwargs):
    super(OrganTab, self).__init__(*args, **kwargs)
    self.ctx = ctx
    self.alfas = None
    self.betas = None
    self.organ_dose = None
    self.organ_names = []
    self.fig = {}
    self.initModel()
    self.initVar()
    self.initUI()
    self.sigConnect()

  def initVar(self):
    self.is_quick_mode = False
    self.show_dosemap = False
    self.show_distmap = False
    self.show_dosedist = False
    self.show_hk = False
    self.ssdec = 0
    self.ssdep = 0
    self.dist_map = None
    self.dose_map = None
    self.organ_dose_mean = 0
    self.organ_dose_std = 0
    self.diameter = 0
    self.ssde = 0
    self.ctdi = 0

  def initModel(self):
    self.protocol_model = QSqlTableModel(db=self.ctx.database.ssde_db)
    self.organ_model = QSqlTableModel(db=self.ctx.database.ssde_db)
    self.organ_dose_model = QSqlTableModel(db=self.ctx.database.ssde_db)

    self.protocol_model.setTable("Protocol")
    self.organ_model.setTable("Organ")
    self.organ_dose_model.setTable("Organ_Dose")

    self.protocol_model.setFilter("Group_ID=1")
    self.organ_dose_model.setFilter("Protocol_ID=1")

    self.protocol_model.select()
    self.organ_model.select()
    self.organ_dose_model.select()

  def sigConnect(self):
    self.method_cb.activated[int].connect(self.on_method_changed)
    self.protocol_cb.activated[int].connect(self.on_protocol_changed)
    self.calc_db_btn.clicked.connect(self.on_calculate_db)
    self.calc_cnt_btn.clicked.connect(self.on_calculate_cnt)
    self.add_cnt_btn.clicked.connect(self.on_contour)
    self.is_quick_mode_chk.stateChanged.connect(self.on_quick_mode_check)
    self.show_hk_chk.stateChanged.connect(self.on_show_hk_check)
    self.show_dosemap_chk.stateChanged.connect(self.on_show_dosemap_check)
    self.show_distmap_chk.stateChanged.connect(self.on_show_distmap_check)
    self.show_dosedist_chk.stateChanged.connect(self.on_show_dosedist_check)
    self.ctx.app_data.modeValueChanged.connect(self.diameter_mode_handle)
    # self.ctx.app_data.diameterValueChanged.connect(self.diameter_handle)
    # self.ctx.app_data.CTDIValueChanged.connect(self.ctdiv_handle)
    # self.ctx.app_data.SSDEValueChanged.connect(self.ssdew_handle)
    self.ctx.app_data.diametersUpdated.connect(self.update_values)
    self.ctx.app_data.ctdivsUpdated.connect(self.update_values)
    self.ctx.app_data.ssdesUpdated.connect(self.update_values)
    self.ctx.app_data.imgChanged.connect(self.img_changed_handle)
    self.ctx.axes.addPolyFinished.connect(self.add_cnt_handle)

  def initUI(self):
    self.figure = PlotDialog()
    self.method_cb = QComboBox()
    self.method_cb.addItems(['MC Data', 'Direct calculation'])

    self.init_db_method_ui()
    self.init_cnt_method_ui()

    self.main_area = QStackedWidget()
    self.main_area.addWidget(self.db_method_ui)
    self.main_area.addWidget(self.cnt_method_ui)
    self.on_method_changed()

    main_layout = QVBoxLayout()
    main_layout.addWidget(QLabel('Method:'))
    main_layout.addWidget(self.method_cb)
    main_layout.addWidget(self.main_area)
    main_layout.addStretch()

    self.setLayout(main_layout)

  def init_db_method_ui(self):
    self.protocol_cb = QComboBox()
    self.protocol_cb.setModel(self.protocol_model)
    self.protocol_cb.setModelColumn(self.protocol_model.fieldIndex('name'))
    self.calc_db_btn = QPushButton('Calculate')

    self.organ_labels = []
    self.organ_edits = [QLineEdit('0') for i in range(28)]
    [organ_edit.setMaximumWidth(70) for organ_edit in self.organ_edits]
    [organ_edit.setReadOnly(True) for organ_edit in self.organ_edits]
    [organ_edit.setAlignment(Qt.AlignRight) for organ_edit in self.organ_edits]

    left = QFormLayout()
    right = QFormLayout()
    grid = QHBoxLayout()
    organ_grpbox = QGroupBox('Organ Dose')
    scroll = QScrollArea()

    for idx, organ_edit in enumerate(self.organ_edits):
      name = self.organ_model.record(idx).value('name')
      self.organ_names.append(name[0])
      label = QLabel(name)
      label.setMaximumWidth(100)
      self.organ_labels.append(label)
      left.addRow(label, organ_edit) if idx<14 else right.addRow(label, organ_edit)

    grid.addLayout(left)
    grid.addLayout(right)
    organ_grpbox.setLayout(grid)
    scroll.setWidget(organ_grpbox)
    scroll.setWidgetResizable(True)

    self.db_method_ui = QGroupBox('', self)
    db_method_layout = QVBoxLayout()
    db_method_layout.addWidget(QLabel('Protocol:'))
    db_method_layout.addWidget(self.protocol_cb)
    db_method_layout.addWidget(self.calc_db_btn)
    db_method_layout.addWidget(scroll)
    db_method_layout.addStretch()
    self.db_method_ui.setLayout(db_method_layout)

  def init_cnt_method_ui(self):
    self.calc_cnt_btn = QPushButton('Calculate')
    self.add_cnt_btn = QPushButton('Add Contour')
    self.is_quick_mode_chk = QCheckBox('Quick Mode')
    self.is_quick_mode_chk.setEnabled(False)
    self.show_dosemap_chk = QCheckBox('Show Dose Map')
    self.show_distmap_chk = QCheckBox('Show Distance Map')
    self.show_dosedist_chk = QCheckBox('Show Histogram')
    self.show_hk_chk = QCheckBox('Show Corr. Factor Graph')

    self.diameter_label = QLabel("<b>Diameter (cm)</b>")
    self.diameter_edit = QLineEdit('0')
    self.ctdiv_edit = QLineEdit('0')
    self.ssdew_edit = QLineEdit('0')
    self.ssdec_edit = QLineEdit('0')
    self.ssdep_edit = QLineEdit('0')
    self.mean_edit = QLineEdit('0')
    self.std_edit = QLineEdit('0')

    edits = [self.diameter_edit, self.ctdiv_edit, self.ssdew_edit, self.ssdec_edit, self.ssdep_edit, self.mean_edit, self.std_edit]
    [edit.setReadOnly(True) for edit in edits]
    self.diameter_mode_handle(DEFF_IMAGE)

    left = QGroupBox('', self)
    right = QGroupBox('', self)
    left_layout = QFormLayout()
    right_layout = QFormLayout()

    left_layout.addRow(self.diameter_label, self.diameter_edit)
    left_layout.addRow(QLabel("<b>CTDI<sub>vol</sub> (mGy)</b>"), self.ctdiv_edit)
    left_layout.addRow(QLabel("<b>SSDE<sub>w</sub> (mGy)</b>"), self.ssdew_edit)
    left_layout.addRow(QLabel("<b>SSDE<sub>c</sub> (mGy)</b>"), self.ssdec_edit)
    left_layout.addRow(QLabel("<b>SSDE<sub>p</sub> (mGy)</b>"), self.ssdep_edit)
    right_layout.addRow(QLabel("<b>Mean (mGy)</b>"), self.mean_edit)
    right_layout.addRow(QLabel("<b>Std. Deviation (mGy)</b>"), self.std_edit)
    left.setLayout(left_layout)
    right.setLayout(right_layout)

    output_area = QHBoxLayout()
    output_area.addWidget(left)
    output_area.addWidget(right)

    opt_grpbox = QGroupBox('Options')
    opt_area = QVBoxLayout()
    opt_area.addWidget(self.is_quick_mode_chk)
    opt_area.addWidget(self.show_distmap_chk)
    opt_area.addWidget(self.show_dosemap_chk)
    opt_area.addWidget(self.show_dosedist_chk)
    opt_area.addWidget(self.show_hk_chk)
    opt_grpbox.setLayout(opt_area)

    btn_layout = QVBoxLayout()
    btn_layout.addStretch()
    btn_layout.addWidget(self.add_cnt_btn)
    btn_layout.addWidget(self.calc_cnt_btn)
    btn_layout.addStretch()

    btn_opt_layout = QHBoxLayout()
    btn_opt_layout.addLayout(btn_layout)
    btn_opt_layout.addWidget(opt_grpbox)

    main_layout = QVBoxLayout()
    main_layout.addLayout(output_area)
    main_layout.addLayout(btn_opt_layout)

    self.cnt_method_ui = QGroupBox('', self)
    self.cnt_method_ui.setLayout(main_layout)

  def plot(self):
    xdict = dict(enumerate(self.organ_names, 1))
    stringaxis = AxisItem(orientation='bottom')
    stringaxis.setTicks([xdict.items()])
    # fm = QFontMetrics(stringaxis.font())
    # minHeight = max(fm.boundingRect(QRect(), Qt.AlignLeft, t).width() for t in xdict.values())
    # stringaxis.setHeight(minHeight + fm.width('     '))

    self.figure = PlotDialog(size=(900,600), straxis=stringaxis)
    self.figure.setTitle('Organ Dose')
    self.figure.axes.showGrid(False,True)
    self.figure.setLabels('', 'Dose' ,'', 'mGy')
    self.figure.bar(x=list(xdict.keys()), height=self.organ_dose, width=.8, brush='g')
    self.figure.show()

  def plot_cnt(self, dose_vec):
    self.figure = PlotDialog()
    self.figure.actionEnabled(True)
    self.figure.trendActionEnabled(False)
    self.figure.opts_dlg.y_mean_chk.setEnabled(False)
    self.figure.opts_dlg.y_stdv_chk.setEnabled(False)
    self.figure.histogram(dose_vec, fillLevel=0, brush=(0,0,255,150), symbol='o', symbolSize=5)
    self.figure.axes.showGrid(True,True)
    self.figure.setLabels('Organ Dose','Frequency','mGy','')
    self.figure.setTitle('Organ Dose')
    self.figure.show()

  def plot_hk(self):
    h, k, dw = self.get_interpolation()
    h_data = h(dw)
    k_data = k(dw)
    diameter = self.diameter
    c = h(diameter)
    p = k(diameter)
    anc_c = (1,0) if diameter>13.575512 else (1,1)
    anc_p = (1,1) if diameter>13.575512 else (1,0)
    self.figure_hk = PlotDialog()
    self.figure_hk.setTitle('Correction Factor')
    self.figure_hk.plot(dw, h_data, pen={'color': "FFFF00", 'width': 2}, symbol=None, name='h_factor')
    self.figure_hk.plot(dw, k_data, pen={'color': "00FFFF", 'width': 2}, symbol=None, name='k_factor')
    self.figure_hk.plot([diameter], [c], symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
    self.figure_hk.plot([diameter], [p], symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
    self.figure_hk.annotate('cfh', pos=(diameter, c), text=f'diameter = {diameter:#.2f}\nh-factor = {c:#.2f}', anchor=anc_c)
    self.figure_hk.annotate('cfk', pos=(diameter, p), text=f'diameter = {diameter:#.2f}\nk-factor = {p:#.2f}', anchor=anc_p)
    self.figure_hk.axes.showGrid(True,True)
    self.figure_hk.setLabels('Diameter','Correction Factor','mm','')
    self.figure_hk.axes.setXRange(np.min(dw), np.max(dw))
    self.figure_hk.axes.setYRange(np.min([np.min(k_data), np.min(h_data)]), np.max([np.max(k_data), np.max(h_data)]))
    self.figure_hk.show()

  def plot_dosemap(self):
    self.figure_dose = ImageViewDialog(unit='dose')
    self.figure_dose.setTitle('Dose Map')
    self.figure_dose.imshow(self.dose_map)
    self.figure_dose.show()

  def plot_img(self, img, title='figure', unit=(None, None)):
    key = title.lower().replace(' ', '_')
    self.fig[key] = ImageViewDialog(unit=unit)
    self.fig[key].setTitle(title)
    self.fig[key].imshow(img)
    self.fig[key].show()

  def getData(self):
    self.alfas = np.array([self.organ_dose_model.record(n).value('alfa') for n in range(self.organ_dose_model.rowCount())])
    self.betas = np.array([self.organ_dose_model.record(n).value('beta') for n in range(self.organ_dose_model.rowCount())])

  def diameter_mode_handle(self, value):
    self.dist_map = None
    self.dose_map = None
    self.add_cnt_btn.setEnabled(True)
    self.add_cnt_btn.setText('Add Contour')
    if value == DW:
      self.diameter_label.setText('<b>Dw (cm)</b>')
      self.show_distmap_chk.setText('Show Water Eq. Distance Map')
      self.is_quick_mode_chk.setEnabled(True)
    else:
      self.diameter_label.setText('<b>Deff (cm)</b>')
      self.show_distmap_chk.setText('Show Effective Distance Map')
      self.is_quick_mode_chk.setCheckState(Qt.Unchecked)
      self.is_quick_mode_chk.setEnabled(False)

  def diameter_handle(self, value):
    self.diameter_edit.setText(f'{value:#.2f}')

  def ctdiv_handle(self, value):
    self.ctdiv_edit.setText(f'{value:#.2f}')

  def ssdew_handle(self, value):
    self.ssdew_edit.setText(f'{value:#.2f}')

  def add_cnt_handle(self, value):
    self.add_cnt_btn.setEnabled(True)
    self.calc_cnt_btn.setEnabled(True)

  def img_changed_handle(self, value):
    if value:
      self.update_values()

  def on_method_changed(self):
    self.main_area.setCurrentIndex(self.method_cb.currentIndex())

  def on_protocol_changed(self, idx):
    self.protocol_id = self.protocol_model.record(idx).value("id")
    self.organ_dose_model.setFilter(f'Protocol_ID={self.protocol_id}')
    self.getData()
    print(self.protocol_id, self.protocol_model.record(idx).value("name"))

  def on_calculate_db(self):
    self.organ_dose = self.ctx.app_data.CTDIv * np.exp(self.alfas*self.ctx.app_data.diameter + self.betas)
    [self.organ_edits[idx].setText(f'{dose:#.2f}') for idx, dose in enumerate(self.organ_dose)]
    self.plot()

  def get_ssde(self):
    h, k, _ = self.get_interpolation()
    self.ssdec = h(self.diameter)*self.ssde
    self.ssdep = k(self.diameter)*self.ssde
    self.ssdec_edit.setText(f'{self.ssdec:#.2f}')
    self.ssdep_edit.setText(f'{self.ssdep:#.2f}')

  def build_dose_map(self):
    from functools import partial
    def avg_profile_line(p2, p1):
      x0, y0 = p1
      x1, y1 = p2
      length = int(np.hypot(x1-x0, y1-y0))
      x = np.linspace(x0, x1, length).astype(int)
      y = np.linspace(y0, y1, length).astype(int)
      return img[x, y].mean()

    cancel = False
    rd = self.ctx.recons_dim
    row, col = self.ctx.get_current_img().shape
    mask = self.get_img_mask(self.ctx.get_current_img(), largest_only=True)
    if mask is not None:
      mask = mask.astype(float)
    mask_pos = np.argwhere(mask==1)
    center = get_center(mask)

    dist_vec = np.sqrt(((mask_pos-center)**2).sum(1))
    if self.ctx.app_data.mode==DW:
      img = self.ctx.get_current_img()
      profile_line_vec = np.zeros_like(dist_vec, dtype=float)
      n = mask_pos.shape[0]
      progress = QProgressDialog(f"Building dose map...", "Stop", 0, n, self)
      progress.setWindowModality(Qt.WindowModal)
      progress.setMinimumDuration(1000)
      profile_line = partial(avg_profile_line, center)
      for idx, pos in enumerate(mask_pos):
        profile_line_vec[idx] = profile_line(pos)
        progress.setValue(idx)
        if progress.wasCanceled():
          cancel = True
          break
      progress.setValue(n)
      if np.isnan(profile_line_vec.sum()):
        profile_line_vec = np.nan_to_num(profile_line_vec)
      dist_vec *= ((profile_line_vec/1000)+1)
    if cancel:
      return

    dist_vec *= (0.1*(rd/row))
    dose_vec = ((dist_vec / ((self.diameter*0.5)-1)) * (self.ssdep-self.ssdec)) + self.ssdec
    self.dist_map = np.zeros_like(mask, dtype=float)
    self.dose_map = np.zeros_like(mask, dtype=float)
    self.dist_map[tuple(mask_pos.T)] = dist_vec
    self.dose_map[tuple(mask_pos.T)] = dose_vec

  def on_calculate_cnt(self):
    if self.ctx.axes.poly is None:
      QMessageBox.warning(None, "Warning", "Organ contour not found.")
      return
    # if self.ctx.app_data.diameter==0 or self.ctx.app_data.SSDE==0:
    #   QMessageBox.warning(None, "Warning", "Diameter and SSDE value not found.")
    #   return

    self.get_ssde()
    if self.dose_map is None:
      self.build_dose_map()
    if self.dose_map is None:
      return

    organ_dose_map = self.ctx.axes.poly.getArrayRegion(self.dose_map, self.ctx.axes.image, returnMappedCoords=False)
    organ_dose_mask_pos = np.argwhere(organ_dose_map!=0)
    organ_dose_vec = organ_dose_map[tuple(organ_dose_mask_pos.T)]
    self.organ_dose_mean = organ_dose_vec.mean()
    self.organ_dose_std = organ_dose_vec.std()
    self.mean_edit.setText(f'{self.organ_dose_mean:#.2f}')
    self.std_edit.setText(f'{self.organ_dose_std:#.2f}')
    if self.show_hk:
      self.plot_hk()
    if self.show_distmap:
      self.plot_img(self.dist_map, 'Distance Map', ('dist','cm'))
    if self.show_dosemap:
      self.plot_img(self.dose_map, 'Dose Map', ('dose','mGy'))
    if self.show_dosedist:
      self.plot_cnt(organ_dose_vec)

  def on_contour(self):
    print(self.ctx.axes.rois)
    if not self.ctx.isImage:
      QMessageBox.warning(None, "Warning", "Open DICOM files first.")
      return
    if self.ctx.axes.poly is None:
      self.ctx.axes.addPoly()
      self.add_cnt_btn.setText("Clear Contour")
      self.add_cnt_btn.setEnabled(False)
      self.calc_cnt_btn.setEnabled(False)
    else:
      self.ctx.axes.clearPoly()
      self.add_cnt_btn.setText("Add Contour")

  def get_organ_mask(self, roi, dose_map):
    img = roi.getArrayRegion(dose_map, self.ctx.axes.image, returnMappedCoords=False)
    return roi.renderShapeMask(img.shape[0],img.shape[1])

  def get_img_mask(self, *args, **kwargs):
    mask = get_mask(*args, **kwargs)
    if mask is None:
      QMessageBox.warning(None, 'Segmentation Failed', 'No object found during segmentation process.')
    return mask

  def get_interpolation(self):
    arr = scio.loadmat(self.ctx.hk_data)['A']
    dw = arr[0]
    hf = arr[5]
    kf = arr[11]
    h = interpolate.interp1d(dw, hf, kind='cubic')
    k = interpolate.interp1d(dw, kf, kind='cubic')
    return (h, k, dw)

  def on_quick_mode_check(self, state):
    self.is_quick_mode = state == Qt.Checked

  def on_show_dosemap_check(self, state):
    self.show_dosemap = state == Qt.Checked

  def on_show_distmap_check(self, state):
    self.show_distmap = state == Qt.Checked

  def on_show_dosedist_check(self, state):
    self.show_dosedist = state == Qt.Checked

  def on_show_hk_check(self, state):
    self.show_hk = state == Qt.Checked

  def update_values(self, val=True):
    if not val:
      return
    self.diameter = self.ctx.app_data.diameters[self.ctx.current_img] if self.ctx.current_img in self.ctx.app_data.diameters.keys() else 0
    self.ctdi = self.ctx.app_data.CTDIvs[self.ctx.current_img] if self.ctx.current_img in self.ctx.app_data.CTDIvs.keys() else 0
    self.ssde = self.ctx.app_data.SSDEs[self.ctx.current_img] if self.ctx.current_img in self.ctx.app_data.SSDEs.keys() else 0
    self.ssdec = 0
    self.ssdep = 0
    self.organ_dose_mean = 0
    self.organ_dose_std = 0
    self.diameter_edit.setText(f'{self.diameter:#.2f}')
    self.ctdiv_edit.setText(f'{self.ctdi:#.2f}')
    self.ssdew_edit.setText(f'{self.ssde:#.2f}')
    self.ssdec_edit.setText(f'{self.ssdec:#.2f}')
    self.ssdep_edit.setText(f'{self.ssdep:#.2f}')
    self.mean_edit.setText(f'{self.organ_dose_mean:#.2f}')
    self.std_edit.setText(f'{self.organ_dose_std:#.2f}')


  def reset_fields(self):
    [organ_edit.setText('0') for organ_edit in self.organ_edits]
    self.protocol_cb.setCurrentIndex(0)
    self.on_protocol_changed(0)
    self.initVar()
    self.ctx.axes.cancel_addPoly()
    self.calc_cnt_btn.setEnabled(True)
    self.add_cnt_btn.setEnabled(True)
    self.add_cnt_btn.setText('Add Contour')
    self.ssdec_edit.setText('0')
    self.ssdep_edit.setText('0')
    self.mean_edit.setText('0')
    self.std_edit.setText('0')
    self.is_quick_mode_chk.setCheckState(Qt.Unchecked)
    self.show_hk_chk.setCheckState(Qt.Unchecked)
    self.show_dosemap_chk.setCheckState(Qt.Unchecked)
    self.show_dosedist_chk.setCheckState(Qt.Unchecked)
