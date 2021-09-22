import sys

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                             QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                             QPushButton, QRadioButton, QSpinBox, QVBoxLayout)
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score
from xlsxwriter.workbook import Workbook


class Axes(pg.PlotWidget):
  addPolyFinished = pyqtSignal(object)
  pg.setConfigOptions(imageAxisOrder='row-major')
  pg.setConfigOptions(antialias=True)
  def __init__(self, lock_aspect=False, *args, **kwargs):
    super(Axes, self).__init__(*args, **kwargs)
    self.initUI()
    self.setupConnect()
    self.setAspectLocked(lock_aspect)

  def initUI(self):
    self.setTitle("")
    self.image = pg.ImageItem()
    self.linePlot = pg.PlotDataItem()
    self.scatterPlot = pg.PlotDataItem()
    self.data = {}
    self.graphs = {}
    self.n_graphs = 0
    self.imagedata = None
    self.lineLAT = None
    self.lineAP = None
    self.ellipse = None
    self.poly = None
    self.poly_pts_pos = []
    self.addItem(self.image)
    self.addItem(self.linePlot)
    self.addItem(self.scatterPlot)
    self.rois = []
    self.alt_image = None

  def setupConnect(self):
    self.image.hoverEvent = self.imageHoverEvent

  def imshow(self, img):
    if img is None:
      return
    self.imagedata = img
    self.invertY(True)
    self.image.setImage(img)
    self.autoRange()

  def add_alt_view(self, img):
    self.alt_image = img
    self.set_alt_image()

  def set_alt_image(self):
    if self.alt_image is not None:
      self.image.setImage(self.alt_image)

  def set_primary_image(self):
    if self.imagedata is not None:
      self.image.setImage(self.imagedata)

  def scatter(self, *args, **kwargs):
    self.scatterPlot.setData(*args, **kwargs)
    self.autoRange()

  def plot_(self, *args, **kwargs):
    self.linePlot.setData(*args, **kwargs)
    self.autoRange()

  def immarker(self, *args, **kwargs):
    self.scatter(*args, **kwargs)
    self.rois.append('marker')

  def plot(self, *args, **kwargs):
    tag = kwargs['name'] if 'name' in kwargs else f'series{self.n_graphs}'
    savedata = True
    if 'savedata' in kwargs.keys():
      savedata = kwargs['savedata']
      kwargs.pop('savedata')
    if savedata:
      if len(args)==1:
        data = args[0]
      elif len(args)==2:
        data = np.vstack(args).T
      else:
        data = None
      self.data[tag] = data
    plot = pg.PlotDataItem()
    plot.setData(*args, **kwargs)
    self.addItem(plot)
    self.graphs[tag] = plot
    self.n_graphs += 1

  def bar(self, *args, **kwargs):
    if 'name' in kwargs:
      tag = kwargs['name']
    else:
      tag = f'series{self.n_graphs}'
    bargraph = pg.BarGraphItem(*args, **kwargs)
    self.addItem(bargraph)
    self.graphs[tag] = bargraph
    self.n_graphs += 1

  def clearImage(self):
    self.imagedata = None
    self.invertY(False)
    self.image.clear()
    self.alt_image = None

  def clear_graph(self, tag):
    self.removeItem(self.graphs[tag])
    self.graphs.pop(tag)
    self.n_graphs -= 1

  def clearGraph(self):
    self.linePlot.clear()
    self.scatterPlot.clear()
    tags = list(self.graphs.keys())
    for tag in tags:
      self.clear_graph(tag)
    try:
      self.rois.remove('marker')
    except:
      pass

  def clearAll(self):
    self.clearImage()
    self.clearGraph()
    self.clearLines()
    self.clearShapes()

  def clearROIs(self):
    self.image.clear()
    self.clearGraph()
    self.clearLines()
    self.clearShapes()
    if self.alt_image is not None:
      self.add_alt_view(self.alt_image)
    else:
      self.imshow(self.imagedata)

  def clearLines(self):
    try:
      self.removeItem(self.lineLAT)
      self.removeItem(self.lineAP)
      self.rois.remove('lineLAT')
      self.rois.remove('lineAP')
      self.lineLAT = None
      self.lineAP = None
    except:
      return

  def clearPoly(self):
    try:
      self.poly_pts_pos = []
      self.removeItem(self.poly)
      self.rois.remove('poly')
    except:
      pass
    self.poly = None

  def clearEllipse(self):
    try:
      self.removeItem(self.ellipse)
      self.rois.remove('ellipse')
    except:
      pass
    self.ellipse = None

  def clearShapes(self):
    self.clearEllipse()
    self.clearPoly()

  def imageHoverEvent(self, event):
    if event.isExit() or len(self.imagedata.shape)!=2:
      self.setTitle("")
      return
    pos = event.pos()
    i, j = pos.x(), pos.y()
    i = int(np.clip(i, 0, self.imagedata.shape[0] - 1))
    j = int(np.clip(j, 0, self.imagedata.shape[1] - 1))
    val = self.imagedata[j, i]
    self.setTitle(f"pixel: ({i:#d}, {j:#d})  value: {val:#g}")

  def addLAT(self, p1, p2):
    if self.lineLAT==None and self.imagedata is not None:
      self.lineLAT = pg.LineSegmentROI([p1, p2], pen={'color': "00FF7F"})
      self.addItem(self.lineLAT)
      self.rois.append('lineLAT')

  def addAP(self, p1, p2):
    if self.lineAP==None and self.imagedata is not None:
      self.lineAP = pg.LineSegmentROI([p1, p2], pen={'color': "00FF7F"})
      self.addItem(self.lineAP)
      self.rois.append('lineAP')

  def addEllipse(self):
    if self.ellipse==None and self.imagedata is not None:
      x,y = self.imagedata.shape
      unit = np.sqrt(x*y)/4
      self.ellipse = pg.EllipseROI(pos=[(x/2)-unit, (y/2)-unit*1.5],size=[unit*2,unit*3], pen={'color': "00FF7F"})
      self.addItem(self.ellipse)
      self.rois.append('ellipse')

  def applyPoly(self, poly):
    if self.poly is None and self.imagedata is not None:
      self.poly = poly
      self.rois.append('poly')
      self.addItem(self.poly)

  def addPoly(self):
    if self.poly is None and self.imagedata is not None:
      self.click_event_bak = self.image.mouseClickEvent
      self.double_click_event_bak = self.image.mouseDoubleClickEvent
      self.image.mouseClickEvent = self.mouse_click_event
      self.image.mouseDoubleClickEvent = self.mouse_double_click_event
      vb = self.image.getViewBox()
      vb.setCursor(Qt.CrossCursor)
      self.poly = pg.PolyLineROI(positions=[(0, 0)])
      self.addItem(self.poly)
      self.poly.clearPoints()
      self.poly_pts_pos = []

  def cancel_addPoly(self):
    if self.poly is not None:
      self.image.mouseClickEvent = self.click_event_bak
      self.image.mouseDoubleClickEvent = self.double_click_event_bak
      self.clearPoly()

  def mouse_double_click_event(self, event):
    if event.button()==1 and 'poly_pos' in self.graphs.keys():
      self.image.mouseClickEvent = self.click_event_bak
      self.image.mouseDoubleClickEvent = self.double_click_event_bak
      vb = self.image.getViewBox()
      vb.unsetCursor()
      self.poly.setPoints(self.poly_pts_pos, closed=True)
      self.rois.append('poly')
      self.clear_graph('poly_pos')
      self.addPolyFinished.emit(self.poly)

  def mouse_click_event(self, event):
    if event.button()==1:
      pos = event.pos()
      self.poly_pts_pos.append((pos.x(), pos.y()))
      poly_pts_pos = np.array(self.poly_pts_pos)
      if 'poly_pos' not in self.graphs.keys():
        self.plot(poly_pts_pos[:,0], poly_pts_pos[:,1], pen=None, symbol='+', symbolPen=None, symbolSize=10, symbolBrush=(255, 0, 0, 255), name='poly_pos')
      else:
        self.graphs['poly_pos'].setData(poly_pts_pos[:,0], poly_pts_pos[:,1])


class PlotDialog(QDialog):
  def __init__(self, size=(640, 480), lock_aspect=False, straxis=None, par=None):
    super(PlotDialog, self).__init__()
    self.setAttribute(Qt.WA_DeleteOnClose)
    self.setWindowFlags(self.windowFlags() |
                        Qt.WindowSystemMenuHint |
                        Qt.WindowMinMaxButtonsHint)
    self.size = size
    self.par = par
    if straxis is None:
      self.axes = Axes(lock_aspect=lock_aspect)
    else:
      self.axes = Axes(lock_aspect=lock_aspect, axisItems={'bottom': straxis})
    self.opts_dlg = PlotOptions(parent=self)
    self.initVar()
    self.initUI()
    self.sigConnect()

  def initVar(self):
    self.n_data = 0
    self.xlabel = None
    self.ylabel = None
    self.x_unit = None
    self.y_unit = None

  def initUI(self):
    self.setWindowTitle('Plot')
    self.layout = QVBoxLayout()
    self.txt = {}
    self.inf_line = {
      'meanx': None, 'meany': None,
      'std1x': None, 'std2x': None,
      'std1y': None, 'std2y': None,
    }
    self.tr_line = False

    btns = QDialogButtonBox.Save | QDialogButtonBox.Close
    self.buttons = QDialogButtonBox(btns)
    self.opts_btn = QPushButton('Options')
    # self.test_btn = QPushButton('Test')

    self.buttons.button(QDialogButtonBox.Close).setAutoDefault(True)
    self.buttons.button(QDialogButtonBox.Close).setDefault(True)
    self.buttons.button(QDialogButtonBox.Save).setText('Save Plot')
    self.buttons.button(QDialogButtonBox.Save).setAutoDefault(False)
    self.buttons.button(QDialogButtonBox.Save).setDefault(False)
    self.opts_btn.setAutoDefault(False)
    self.opts_btn.setDefault(False)
    # self.test_btn.setAutoDefault(False)
    # self.test_btn.setDefault(False)

    self.actionEnabled(False)

    btn_layout = QHBoxLayout()
    btn_layout.addWidget(self.opts_btn)
    # btn_layout.addWidget(self.test_btn)
    btn_layout.addStretch()
    btn_layout.addWidget(self.buttons)

    self.layout.addWidget(self.axes)
    self.layout.addLayout(btn_layout)
    self.setLayout(self.layout)
    self.resize(self.size[0], self.size[1])
    # self.crosshair()
    # self.axis_line()

  def sigConnect(self):
    self.buttons.rejected.connect(self.on_close)
    self.buttons.accepted.connect(self.on_save)
    self.opts_btn.clicked.connect(self.on_opts_dialog)
    # self.test_btn.clicked.connect(self.on_test)
    [opt.stateChanged.connect(self.apply_stddev_opts) for opt in self.opts_dlg.stdv_chks]
    [opt.stateChanged.connect(self.apply_mean_opts) for opt in self.opts_dlg.mean_chks]
    self.opts_dlg.trdl_btngrp.buttonClicked[int].connect(self.apply_trendline_opts)
    self.opts_dlg.poly_ordr_spn.valueChanged.connect(self.on_poly_order_changed)
    # self.proxy = pg.SignalProxy(self.axes.linePlot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

  def on_test(self):
    pass

  def plot(self, *args, **kwargs):
    self.axes.plot(*args, **kwargs)
    self.n_data += 1

  def scatter(self, *args, **kwargs):
    self.axes.scatterPlot.clear()
    self.axes.scatter(*args, **kwargs)
    self.n_data += 1

  def histogram(self, data, bins=20, **kwargs):
    y, x = np.histogram(data, bins=bins)
    self.plot(x, y, stepMode=True, savedata=False, **kwargs)
    self.axes.setXRange(np.min(x), np.max(x))
    self.axes.setYRange(np.min(y), np.max(y))
    tag = kwargs['name'] if 'name' in kwargs.keys() else f'series{self.n_data-1}'
    self.axes.data[tag] = np.stack((data, data)).T

  def annotate(self, tag, pos=(0,0), angle=0, *args, **kwargs):
    txt = pg.TextItem(*args, **kwargs)
    txt.setPos(pos[0], pos[1])
    txt.setAngle(angle)
    self.txt[tag] = txt
    self.axes.addItem(txt)

  def clearAnnotation(self, tag):
    if self.txt:
      self.axes.removeItem(self.txt[tag])
      self.txt.pop(tag)

  def setLabels(self, xlabel, ylabel, x_unit=None, y_unit=None, x_prefix=None, y_prefix=None):
    self.xlabel = xlabel
    self.ylabel = ylabel
    self.x_unit = x_unit
    self.y_unit = y_unit
    self.axes.setLabel('bottom', xlabel, x_unit, x_prefix)
    self.axes.setLabel('left', ylabel, y_unit, y_prefix)

  def setTitle(self, title):
    self.setWindowTitle('Graph of '+title)
    self.axes.setTitle(title)

  def actionEnabled(self, state):
    self.meanActionEnabled(state)
    self.stddevActionEnabled(state)
    self.trendActionEnabled(state)

  def meanActionEnabled(self, state):
    [opt.setEnabled(state) for opt in self.opts_dlg.mean_chks]

  def trendActionEnabled(self, state):
    [opt.setEnabled(state) for opt in self.opts_dlg.trdl_opts]

  def stddevActionEnabled(self, state):
    [opt.setEnabled(state) for opt in self.opts_dlg.stdv_chks]

  def on_avgline(self, axis):
    name = "mean"
    if self.inf_line[name+axis]:
      return
    x, y = self.get_data()

    if x is None or y is None:
      return
    mean = x.mean() if axis=='x' else y.mean()
    anchor = (0, 1) #if axis=='x' else (0, 0)
    pos = (mean, max(y)) if axis=='x' else (max(x), mean)
    angle = 0 if axis=='y' else 90
    unit = self.x_unit if axis=='x' else self.y_unit
    self.create_inf_line(mean, axis, name, pg.mkPen(color='c', width=2))
    self.annotate(name+axis, anchor=anchor, pos=pos, angle=angle, text=f'mean_{axis}: {mean:#.2f} {unit}')

  def get_data(self):
    max_size = 0
    max_tag = None
    for tag, data in self.axes.data.items():
      if data.shape[0] > max_size:
        max_size = data.shape[0]
        max_tag = tag

    if max_size==0 or max_tag is None:
      return None, None
    return self.axes.data[max_tag].T

  def get_plot_data(self):
    max_size = 0
    max_idx = 0
    for idx, curve in enumerate(self.axes.plotItem.curves):
      curve_data = curve.getData()
      if curve_data[0] is None or curve.name()=='trendline':
        continue
      size = curve_data[0].size
      if size > max_size:
        max_size = size
        max_idx = idx

    if max_size==0:
      return None, None
    return self.axes.plotItem.curves[max_idx].getData()

  def on_stddev(self, axis):
    name1 = 'std1'
    name2 = 'std2'
    if self.inf_line[name1+axis] and self.inf_line[name2+axis]:
      return

    x, y = self.get_data()
    if x is None or y is None:
      return

    dep_v = x if axis=='x' else y
    indep_v = y if axis=='x' else x
    mean = dep_v.mean()
    std = dep_v.std()

    pos1 = (max(x), mean+std) if axis=='y' else (mean+std, max(y))
    pos2 = (max(x), mean-std) if axis=='y' else (mean-std, max(y))
    anchor1 = (0,1) if axis=='y' else (0,1)
    anchor2 = (0,1) if axis=='y' else (0,1)
    angle = 0 if axis=='y' else 90
    unit = self.x_unit if axis=='x' else self.y_unit

    pen = pg.mkPen(color='m', width=2)
    self.create_inf_line(mean+std, axis, name1, pen)
    self.create_inf_line(mean-std, axis, name2, pen)
    self.annotate(name1+axis, anchor=anchor1, pos=pos1, angle=angle, text=f'std_{axis}: +{std:#.2f} {unit}')
    self.annotate(name2+axis, anchor=anchor2, pos=pos2, angle=angle, text=f'std_{axis}: -{std:#.2f} {unit}')

  def on_trendline(self, method):
    if self.tr_line:
      self.clear_trendline()

    x, y = self.get_data()
    if x is None or y is None:
      return

    model = CurveFit(x,y)
    if method=='linear' or method=='polynomial':
      degree = 1 if method=='linear' else self.opts_dlg.poly_ordr_spn.value()
      param, r2, predict = model.polyfit(degree)
      eq = model.get_poly_eq(param)
    elif method=='exponential':
      param, r2, predict = model.expfit()
      eq = model.get_exp_eq(param)
    elif method=='logarithmic':
      param, r2, predict = model.logfit()
      eq = model.get_log_eq(param)
    else:
      return

    pos = ((x[0]+x[-1])//2, (y[0]+y[-1])//2)
    x_trend = np.arange(x[0],x[-1]+0.01,0.01)
    self.plot(x_trend, predict(x_trend), name='trendline', pen={'color': "FF0000", 'width': 2.5})
    self.annotate('tr', pos=pos, text=f'y = {eq}\nR² = {r2:#.4f}')
    self.tr_line = True

  def clear_stddev(self, axis):
    if self.inf_line['std1'+axis] and self.inf_line['std2'+axis]:
      self.clear_inf_line(axis, 'std1')
      self.clear_inf_line(axis, 'std2')
      self.clearAnnotation('std1'+axis)
      self.clearAnnotation('std2'+axis)

  def clear_mean(self, axis):
    if self.inf_line['mean'+axis]:
      self.clear_inf_line(axis, 'mean')
      self.clearAnnotation('mean'+axis)

  def clear_trendline(self):
    if self.tr_line:
      self.tr_line = False
      self.axes.clear_graph('trendline')
      self.clearAnnotation('tr')

  def apply_mean_opts(self):
    self.on_avgline('x') if self.opts_dlg.x_mean_chk.isChecked() else self.clear_mean('x')
    self.on_avgline('y') if self.opts_dlg.y_mean_chk.isChecked() else self.clear_mean('y')

  def apply_stddev_opts(self):
    self.on_stddev('x') if self.opts_dlg.x_stdv_chk.isChecked() else self.clear_stddev('x')
    self.on_stddev('y') if self.opts_dlg.y_stdv_chk.isChecked() else self.clear_stddev('y')

  def apply_trendline_opts(self, idx):
    button = self.opts_dlg.trdl_btngrp.button(idx)
    method = button.text().lower()
    self.on_trendline(method)

  def on_poly_order_changed(self):
    self.on_trendline('polynomial')

  def on_opts_dialog(self):
    if self.opts_dlg.isVisible():
       self.opts_dlg.close()
       return
    rect = self.frameGeometry()
    x, y = rect.topLeft().x(), rect.topLeft().y()
    self.opts_dlg.show()
    if x-self.opts_dlg.width() < 0:
      self.opts_dlg.move(x, y)
    else:
      self.opts_dlg.move(x-self.opts_dlg.width(), y)

  def on_close(self):
    self.close()

  def on_save(self):
    accepted_format = """
      PNG (*.png);;
      TIFF (*.tif;*.tiff);;
      JPEG (*.jpg;*.jpeg;*.jpe;*.jfif);;
      Bitmap (*.bmp);;
      Scalable Vector Graphics (*.svg);;
      Comma-Separated Value (*.csv);;
      Microsoft Excel Workbook (*.xlsx)
    """
    filename, _ = QFileDialog.getSaveFileName(self, "Save plot as image...", self.windowTitle(), accepted_format)
    if not filename:
      return
    if not filename.lower().endswith(('.csv', '.svg', '.xlsx')):
      exporter = pg.exporters.ImageExporter(self.axes.plotItem)
      exporter.parameters()['width'] *= 2
    elif filename.lower().endswith('.csv'):
      exporter = CSVExporter(self.axes.plotItem, xheader=self.xlabel, yheader=self.ylabel)
    elif filename.lower().endswith('.xlsx'):
      exporter = XLSXExporter(self.axes.plotItem, xheader=self.xlabel, yheader=self.ylabel)
    elif filename.lower().endswith('.svg'):
      exporter = pg.exporters.SVGExporter(self.axes.plotItem)
    else:
      return
    exporter.export(filename)

  def create_inf_line(self, value, axis, name, pen=None):
    if axis=='x' or axis=='y':
      angle = 90 if axis=='x' else 0
    else:
      return
    self.inf_line[name+axis] = pg.InfiniteLine(angle=angle, movable=False, pen=pen)
    self.axes.addItem(self.inf_line[name+axis])
    self.inf_line[name+axis].setPos(value)
    self.inf_line[name+axis].setZValue(-10)

  def bar(self, *args, **kwargs):
    self.axes.clearAll()
    self.axes.bar(*args, **kwargs)

  def clear_inf_line(self, axis, name):
    if self.inf_line[name+axis]:
      self.axes.removeItem(self.inf_line[name+axis])
      self.inf_line[name+axis] = None

  def axis_line(self):
    self.y_axis = pg.InfiniteLine(angle=90, movable=False, pen={'color': "FFFFFF", 'width': 1.5})
    self.x_axis = pg.InfiniteLine(angle=0, movable=False, pen={'color': "FFFFFF", 'width': 1.5})
    self.y_axis.setZValue(-100)
    self.x_axis.setZValue(-100)
    self.axes.addItem(self.y_axis, ignoreBounds=True)
    self.axes.addItem(self.x_axis, ignoreBounds=True)

  def crosshair(self):
    self.vLine = pg.InfiniteLine(angle=90, movable=False, pen={'color': "FFFFFF", 'width': 1.5})
    self.hLine = pg.InfiniteLine(angle=0, movable=False, pen={'color': "FFFFFF", 'width': 1.5})
    self.axes.addItem(self.vLine, ignoreBounds=True)
    self.axes.addItem(self.hLine, ignoreBounds=True)

  def mouseMoved(self, evt):
    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
    if self.axes.sceneBoundingRect().contains(pos):
      mousePoint = self.axes.plotItem.vb.mapSceneToView(pos)
      index = int(mousePoint.x())
      # if index > 0 and index < len(data1):
      self.axes.setTitle("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y=%0.1f</span>" % (mousePoint.x(), mousePoint.y()))
      self.vLine.setPos(mousePoint.x())
      self.hLine.setPos(mousePoint.y())

  def closeEvent(self, event):
    if self.opts_dlg.isVisible():
      self.opts_dlg.close()
    if self.par is not None:
      self.par.plot_dialog_closed()


class XLSXExporter(pg.exporters.CSVExporter):
  def __init__(self, item, xheader=None, yheader=None):
    pg.exporters.CSVExporter.__init__(self, item)
    self.item = item
    self.xheader = xheader
    self.yheader = yheader

  def export(self, fileName=None):
    if fileName is None:
      self.fileSaveDialog(filter=["*.xlsx"])
      return

    data = []
    header = []

    # get header and data
    for i, c in enumerate(self.item.curves):
      cd = c.getData()
      if cd[0] is None:
        continue
      data.append(cd)
      if self.xheader is not None and self.yheader is not None:
        xName = f'{self.xheader}_{i:#d}'
        yName = f'{self.yheader}_{i:#d}'
      elif hasattr(c, 'implements') and c.implements('plotData') and c.name() is not None:
        name = c.name().replace('"', '""') + '_'
        xName, yName = '"'+name+'x"', '"'+name+'y"'
      else:
        xName = 'x%d' % i
        yName = 'y%d' % i
      header.extend([xName, yName])

    # create and open workbook
    workbook = Workbook(fileName)
    worksheet = workbook.add_worksheet()
    bold = workbook.add_format({'bold': True})
    numCols = len(data)*2

    # write header
    for col in range(numCols):
      worksheet.write(0, col, header[col], bold)

    # write data
    for i, d in enumerate(data):
      numCols = len(d)
      numRows = len(d[0])
      for row in range(1, numRows+1):
        for col in range(i*2, i*2+numCols):
          try:
            worksheet.write(row, col, d[col-i*2][row-1])
          except:
            continue

    # close workbook
    workbook.close()


class CSVExporter(pg.exporters.CSVExporter):
  def __init__(self, item, xheader=None, yheader=None):
    pg.exporters.CSVExporter.__init__(self, item)
    self.item = item
    self.xheader = xheader
    self.yheader = yheader

  def export(self, fileName=None):
    if fileName is None:
      self.fileSaveDialog(filter=["*.csv"])
      return

    data = []
    header = []
    sep = ','

    for i, c in enumerate(self.item.curves):
      cd = c.getData()
      if cd[0] is None:
        continue
      data.append(cd)
      if self.xheader is not None and self.yheader is not None:
        xName = f'{self.xheader}_{i:#d}'
        yName = f'{self.yheader}_{i:#d}'
      elif hasattr(c, 'implements') and c.implements('plotData') and c.name() is not None:
        name = c.name().replace('"', '""') + '_'
        xName, yName = '"'+name+'x"', '"'+name+'y"'
      else:
        xName = 'x%d' % i
        yName = 'y%d' % i
      header.extend([xName, yName])

    with open(fileName, 'w') as fd:
      fd.write(sep.join(header) + '\n')
      i = 0
      numFormat = '%%0.%dg' % self.params['precision']
      numRows = max([len(d[0]) for d in data])
      for i in range(numRows):
        for j, d in enumerate(data):
          # print(d)
          # write x value if this is the first column, or if we want
          # x for all rows
          if d is not None and i < len(d[0]):
            fd.write(numFormat % d[0][i] + sep)
          else:
            fd.write(' %s' % sep)

          # write y value
          if d is not None and i < len(d[1]):
            fd.write(numFormat % d[1][i] + sep)
          else:
            fd.write(' %s' % sep)
        fd.write('\n')


class AxisItem(pg.AxisItem):
  def __init__(self, *args, **kwargs):
    super(AxisItem, self).__init__(*args, **kwargs)

  def drawPicture(self, p, axisSpec, tickSpecs, textSpecs):
    p.setRenderHint(p.Antialiasing, False)
    p.setRenderHint(p.TextAntialiasing, True)

    ## draw long line along axis
    pen, p1, p2 = axisSpec
    p.setPen(pen)
    p.drawLine(p1, p2)
    p.translate(0.5,0)  ## resolves some damn pixel ambiguity

    ## draw ticks
    for pen, p1, p2 in tickSpecs:
      p.setPen(pen)
      p.drawLine(p1, p2)

    # Draw all text
    if self.style['tickFont'] is not None:
      p.setFont(self.style['tickFont'])
    p.setPen(self.textPen())
    for rect, flags, text in textSpecs:
      # p.save()
      # p.translate(rect.x(), rect.y())
      # p.rotate(-90)
      # p.drawText(-rect.width(), rect.height(), rect.width(), rect.height(), int(flags), text)
      p.drawText(rect, int(flags), text)
      # p.restore()


class CurveFit:
  def __init__(self, x_data=[], y_data=[]):
    self.set_data(x_data, y_data)

  def polyfit(self, degree=2):
    params = np.polyfit(self.x_data, self.y_data, degree)
    predict = np.poly1d(params)
    r2 = r2_score(self.y_data, predict(self.x_data))
    return params, r2, predict

  def expfit(self, p0=None):
    params, cov = curve_fit(lambda t,a,b: a*np.exp(b*t), self.x_data,  self.y_data, p0=p0)
    a,b = params
    predict = lambda x: a*np.exp(b*x)
    r2 = r2_score(self.y_data, predict(self.x_data))
    return params, r2, predict

  def logfit(self):
    params, cov = curve_fit(lambda t,a,b: a+b*np.log(t),  self.x_data,  self.y_data)
    a,b = params
    predict = lambda x: a+b*np.log(x)
    r2 = r2_score(self.y_data, predict(self.x_data))
    return params, r2, predict

  def set_data(self, x_data, y_data):
    self.x_data = x_data
    self.y_data = y_data

  def get_exp_eq(self, p, var_string='x', prec=4):
    superscript = str.maketrans("0123456789abcdefghijklmnoprstuvwxyz.", "⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ⋅")
    numformat = '%%0.%df' % prec
    a,b = p
    str_a = numformat % a
    raw_str_b = numformat % b
    str_b = raw_str_b.translate(superscript)
    str_var = var_string.translate(superscript)
    return str_a + 'e' + str_b + str_var

  def get_log_eq(self, p, var_string='x', prec=4):
    numformat = '%%0.%df' % prec
    a,b = p
    if b<0:
      sign = ' - '
      b = -b
    else:
      sign = ' + '
    str_a = numformat % a
    str_b = numformat % b
    return str_a + sign + str_b + f'ln({var_string})'

  def get_poly_eq(self, p, var_string='x', prec=4):
    res = ''
    first_pow = len(p) - 1
    superscript = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    numformat = '%%0.%df' % prec
    for i, coef in enumerate(p):
      power = first_pow - i

      if coef:
        if coef < 0:
          sign, coef = (' - ' if res else '- '), -coef
        elif coef > 0: # must be true
          sign = (' + ' if res else '')
        else:
          sign = ''

        str_coef = '' if coef == 1 and power != 0 else numformat%coef

        if power == 0:
          str_power = ''
        elif power == 1:
          str_power = var_string
        else:
          raw_str_power = var_string + str(power)
          str_power = raw_str_power.translate(superscript)

        res += sign + str_coef + str_power
    return res


class PlotOptions(QDialog):
  def __init__(self, *args, **kwargs):
    super(PlotOptions, self).__init__(*args, **kwargs)
    self.initUI()
    self.sigConnect()

  def initUI(self):
    self.setWindowTitle('Options')

    self.x_mean_chk = QCheckBox('x-data')
    self.y_mean_chk = QCheckBox('y-data')
    self.mean_chks = [self.x_mean_chk, self.y_mean_chk]

    mean_grpbox = QGroupBox('Mean')
    mean_layout = QVBoxLayout()
    mean_layout.addWidget(self.x_mean_chk)
    mean_layout.addWidget(self.y_mean_chk)
    mean_grpbox.setLayout(mean_layout)

    self.x_stdv_chk = QCheckBox('x-data')
    self.y_stdv_chk = QCheckBox('y-data')
    self.stdv_chks = [self.x_stdv_chk, self.y_stdv_chk]

    stdv_grpbox = QGroupBox('Standard Deviation')
    stdv_layout = QVBoxLayout()
    stdv_layout.addWidget(self.x_stdv_chk)
    stdv_layout.addWidget(self.y_stdv_chk)
    stdv_grpbox.setLayout(stdv_layout)

    self.none_trdl_btn = QRadioButton('None')
    self.linr_trdl_btn = QRadioButton('Linear')
    self.poly_trdl_btn = QRadioButton('Polynomial')
    self.exp_trdl_btn = QRadioButton('Exponential')
    self.log_trdl_btn = QRadioButton('Logarithmic')
    self.poly_ordr_spn = QSpinBox()
    self.trdl_btngrp = QButtonGroup()
    self.trdl_opts = [self.none_trdl_btn, self.linr_trdl_btn, self.poly_trdl_btn, self.exp_trdl_btn, self.log_trdl_btn]

    self.trdl_btngrp.addButton(self.none_trdl_btn)
    self.trdl_btngrp.addButton(self.linr_trdl_btn)
    self.trdl_btngrp.addButton(self.poly_trdl_btn)
    self.trdl_btngrp.addButton(self.exp_trdl_btn)
    self.trdl_btngrp.addButton(self.log_trdl_btn)

    self.none_trdl_btn.setChecked(True)
    self.poly_ordr_spn.setValue(2)
    self.poly_ordr_spn.setMinimum(2)
    self.poly_ordr_spn.setMaximumWidth(50)
    self.poly_ordr_spn.setEnabled(False)

    trdl_grpbox = QGroupBox('Trendline')
    trdl_layout = QFormLayout()
    trdl_layout.addRow(self.none_trdl_btn, QLabel(''))
    trdl_layout.addRow(self.linr_trdl_btn, QLabel(''))
    trdl_layout.addRow(self.poly_trdl_btn, self.poly_ordr_spn)
    trdl_layout.addRow(self.exp_trdl_btn, QLabel(''))
    trdl_layout.addRow(self.log_trdl_btn, QLabel(''))
    trdl_grpbox.setLayout(trdl_layout)

    self.buttons = QDialogButtonBox(QDialogButtonBox.Close)

    layout = QVBoxLayout()
    layout.addWidget(mean_grpbox)
    layout.addWidget(stdv_grpbox)
    layout.addWidget(trdl_grpbox)
    layout.addWidget(self.buttons)

    self.setLayout(layout)

  def sigConnect(self):
    self.buttons.rejected.connect(self.reject)
    [button.toggled.connect(self.on_trdl_changed) for button in self.trdl_btngrp.buttons()]

  def on_trdl_changed(self):
    self.poly_ordr_spn.setEnabled(self.sender().text().lower() == 'polynomial')


class ImageViewDialog(QDialog):
  pg.setConfigOptions(antialias=True)
  def __init__(self, size=(640, 480), unit=(None, None), *args, **kwargs):
    super(ImageViewDialog, self).__init__(*args, **kwargs)
    self.setAttribute(Qt.WA_DeleteOnClose)
    self.setWindowFlags(self.windowFlags() |
                        Qt.WindowSystemMenuHint |
                        Qt.WindowMinMaxButtonsHint)
    self.measure = 'value' if unit[0] is None else unit[0]
    self.unit = '' if unit[1] is None else unit[1]
    self.resize(size[0], size[1])
    self.initUI()
    self.sigConnect()
    self.apply_cmap('thermal')

  def initUI(self):
    self.plot_item = pg.PlotItem()
    self.plot_item.setLabel(axis='left')
    self.plot_item.setLabel(axis='bottom')
    self.plot_item.setTitle("")

    self.image_item = pg.ImageItem()
    self.image_item.hoverEvent = self.imageHoverEvent

    self.imv = pg.ImageView(view=self.plot_item, imageItem=self.image_item)
    self.imv.ui.roiBtn.hide()
    self.imv.ui.menuBtn.hide()

    self.cmap_cb = QComboBox()
    self.cmap_cb.addItems(["thermal", "flame", "yellowy",
                           "bipolar", "spectrum", "cyclic",
                           "greyclip", "grey", "viridis",
                           "inferno", "plasma", "magma"])

    cb_layout = QHBoxLayout()
    cb_layout.addStretch()
    cb_layout.addWidget(QLabel('Color map:'))
    cb_layout.addWidget(self.cmap_cb)

    layout = QVBoxLayout()
    layout.addWidget(self.imv)
    layout.addLayout(cb_layout)
    self.setLayout(layout)

  def sigConnect(self):
    self.cmap_cb.activated[str].connect(self.apply_cmap)

  def imshow(self, img):
    self.image_data = img
    self.imv.setImage(img)
    img_flat = img.flatten()
    self.imv.setLevels(min=np.min(img_flat[np.nonzero(img_flat)]), max=np.max(img_flat))

  def add_roi(self, roi):
    handles = roi.getHandles()
    positions = []
    for h in handles:
      pos = (h.pos().x(), h.pos().y())
      positions.append(pos)
    r = pg.PolyLineROI(positions=positions, closed=True)
    self.plot_item.addItem(r)

  def set_cmap(self, colors):
    cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, len(colors)), color=colors)
    self.imv.setColorMap(cmap)

  def setTitle(self, title):
    self.setWindowTitle(title)

  def apply_cmap(self, name):
    self.imv.setPredefinedGradient(name)

  def imageHoverEvent(self, event):
    if event.isExit():
      self.plot_item.setTitle("")
      return
    pos = event.pos()
    i, j = pos.x(), pos.y()
    i = int(np.clip(i, 0, self.image_data.shape[0] - 1))
    j = int(np.clip(j, 0, self.image_data.shape[1] - 1))
    val = self.image_data[j, i]
    self.plot_item.setTitle(f"location: ({i:#d}, {j:#d})  {self.measure}: {val:#g}{self.unit}")


if __name__ == '__main__':
  app = QApplication(sys.argv)
  dialog = PlotDialog()
  dialog.actionEnabled(True)
  dialog.show()
  sys.exit(app.exec_())
