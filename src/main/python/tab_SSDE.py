import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlTableModel
from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                             QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QRadioButton, QScrollArea, QSpinBox, QVBoxLayout)

from constants import *
from custom_widgets import HSeparator
from db import get_records
from Plot import PlotDialog


class SSDETab(QDialog):
  def __init__(self, ctx, *args, **kwargs):
    super(SSDETab, self).__init__(*args, **kwargs)
    self.ctx = ctx
    self.show_graph = False
    self.show_ssde_graph = False
    self.all_slices = False
    self.use_avg = False
    self.d3_method = 'slice step'
    self.current_idx = 0
    self.initVar()
    self.initModel()
    self.initUI()
    self.sigConnect()

  def initVar(self):
    self.diameter = 0
    self.CTDIv = 0
    self.convf = 0
    self.SSDE = 0
    self.DLPc = 0
    self.effdose = 0
    self.ctdivs = []
    self.diameters = []
    self.idxs = []
    self.ssdes = []
    self.display = {
      'ctdi': None,
      'diameter': None,
      'cf': None,
      'ssde': None,
      'dlp': None,
      'dlpc': None,
      'effdose': None,
    }

  def set_data(self):
    self.display['ctdi'] = self.CTDIv
    self.display['diameter'] = self.diameter
    self.display['cf'] = self.convf
    self.display['ssde'] = self.SSDE
    self.display['dlp'] = self.ctx.app_data.DLP
    self.display['dlpc'] = self.DLPc
    self.display['effdose'] = self.effdose

  def initModel(self):
    self.protocol_model = QSqlTableModel(db=self.ctx.database.ssde_db)
    self.protocol_model.setTable("Protocol")
    self.protocol_model.setFilter("Group_ID=1")
    self.protocol_model.select()

    self.report_model = QSqlTableModel(db=self.ctx.database.ssde_db)
    self.report_model.setTable("Report")
    self.report_model.select()

    self.cf_model = QSqlTableModel(db=self.ctx.database.ssde_db)
    self.cf_model.setTable("ConversionFactor")
    self.cf_model.setFilter("report_id=1")
    self.cf_model.select()

    self.effdose_model = QSqlTableModel(db=self.ctx.database.ssde_db)
    self.effdose_model.setTable("Effective_Dose")
    self.effdose_model.select()

  def initUI(self):
    self.hidden_btn = QPushButton('check') # for debug
    self.hidden_btn.setVisible(False)

    self.figure = PlotDialog()
    self.protocol_cb = QComboBox()
    self.protocol_cb.setModel(self.protocol_model)
    self.protocol_cb.setModelColumn(self.protocol_model.fieldIndex('name'))
    self.report_cb = QComboBox()
    self.report_cb.setModel(self.report_model)
    self.report_cb.setModelColumn(self.report_model.fieldIndex('name'))
    self.plot_chk = QCheckBox('Show Graph')
    self.avg_chk = QCheckBox('Use Avg. Value')
    self.show_ssde_graph_chk = QCheckBox('Show SSDE Graph')

    self.d3_opts_cb = QComboBox()
    self.d3_opts_cb.addItems(['One slice', 'Z-axis'])
    self.d3opts_rbtns = [QRadioButton('Slice Step'), QRadioButton('Slice Number'), QRadioButton('Regional')]
    self.d3opts_rbtns[0].setChecked(True)
    self.slice1_sb = QSpinBox()
    self.slice2_sb = QSpinBox()
    self.to_lbl = QLabel('to')

    self.slice1_sb.setMaximum(self.ctx.total_img)
    self.slice1_sb.setMinimum(1)
    self.slice1_sb.setMinimumWidth(50)
    self.slice2_sb.setMaximum(self.ctx.total_img)
    self.slice2_sb.setMinimum(1)
    self.slice2_sb.setMinimumWidth(50)
    self.to_lbl.setHidden(True)
    self.slice2_sb.setHidden(True)

    self.calc_btn = QPushButton('Calculate')
    self.save_btn = QPushButton('Save')

    self.calc_btn.setAutoDefault(True)
    self.calc_btn.setDefault(True)
    self.save_btn.setAutoDefault(False)
    self.save_btn.setDefault(False)

    self.ctdiv_edit = QLineEdit(f'{self.ctx.app_data.CTDIv}')
    self.diameter_edit = QLineEdit(f'{self.ctx.app_data.diameter}')
    self.convf_edit = QLineEdit(f'{self.ctx.app_data.convf}')
    self.ssde_edit = QLineEdit(f'{self.ctx.app_data.SSDE}')
    self.dlp_edit = QLineEdit(f'{self.ctx.app_data.DLP}')
    self.dlpc_edit = QLineEdit(f'{self.ctx.app_data.DLPc}')
    self.effdose_edit = QLineEdit(f'{self.ctx.app_data.effdose}')

    self.current_dlabel = '<b>Deff (cm)</b>'
    self.diameter_label = QLabel(self.current_dlabel)
    self.ctdiv_label = QLabel('<b>CTDI<sub>vol</sub> (mGy)</b>')
    self.ssde_label = QLabel('<b>SSDE (mGy)</b>')

    self.diameter_mode_handle(DEFF_IMAGE)

    self.next_tab_btn = QPushButton('Next')
    self.prev_tab_btn = QPushButton('Previous')

    self.next_tab_btn.setAutoDefault(False)
    self.next_tab_btn.setDefault(False)
    self.prev_tab_btn.setAutoDefault(False)
    self.prev_tab_btn.setDefault(False)
    self.next_tab_btn.setVisible(False)

    edits = [
      self.ctdiv_edit,
      self.diameter_edit,
      self.convf_edit,
      self.ssde_edit,
      self.dlp_edit,
      self.dlpc_edit,
      self.effdose_edit,
    ]

    [edit.setReadOnly(True) for edit in edits]
    [edit.setAlignment(Qt.AlignRight) for edit in edits]

    slice_layout = QHBoxLayout()
    slice_layout.addWidget(self.slice1_sb)
    slice_layout.addWidget(self.to_lbl)
    slice_layout.addWidget(self.slice2_sb)
    slice_layout.addStretch()

    self.d3opts_grpbox = QGroupBox('Z-axis Options')
    dcm_d3opts_layout = QVBoxLayout()
    [dcm_d3opts_layout.addWidget(btn) for btn in self.d3opts_rbtns]
    dcm_d3opts_layout.addLayout(slice_layout)
    dcm_d3opts_layout.addWidget(self.show_ssde_graph_chk)
    dcm_d3opts_layout.addStretch()
    dcm_d3opts_layout.setContentsMargins(11,3,11,3)
    self.d3opts_grpbox.setLayout(dcm_d3opts_layout)
    self.d3opts_grpbox.setVisible(False)

    left_grpbox = QGroupBox()
    left_layout = QFormLayout()
    left_layout.addRow(self.ctdiv_label, self.ctdiv_edit)
    left_layout.addRow(self.diameter_label, self.diameter_edit)
    left_layout.addRow(QLabel('<b>Conv Factor</b>'), self.convf_edit)
    left_layout.addRow(self.ssde_label, self.ssde_edit)
    # left_layout.addRow(QLabel('<b>Option</b>'), self.d3_opts_cb)
    left_layout.addRow(self.calc_btn, self.plot_chk)
    left_layout.addRow(QLabel(''))
    # left_layout.addRow(self.calc_btn, self.avg_chk)
    # left_layout.addRow(QLabel(''), self.plot_chk)
    left_layout.addRow(self.save_btn, QLabel(''))
    left_grpbox.setLayout(left_layout)

    right_grpbox = QGroupBox()
    right_layout = QFormLayout()
    right_layout.addRow(QLabel('<b>DLP (mGy-cm)</b>'), self.dlp_edit)
    right_layout.addRow(QLabel('<b>DLP<sub>c</sub> (mGy-cm)</b>'), self.dlpc_edit)
    right_layout.addRow(QLabel('<b>Effective Dose (mSv)</b>'), self.effdose_edit)
    right_grpbox.setLayout(right_layout)

    r_layout = QVBoxLayout()
    r_layout.addWidget(right_grpbox)
    r_layout.addWidget(self.d3opts_grpbox)

    h = QHBoxLayout()
    h.addWidget(left_grpbox)
    h.addLayout(r_layout)

    tab_nav = QHBoxLayout()
    tab_nav.addWidget(self.prev_tab_btn)
    tab_nav.addWidget(self.hidden_btn)
    tab_nav.addStretch()
    tab_nav.addWidget(self.next_tab_btn)

    main_layout = QVBoxLayout()
    main_layout.addWidget(QLabel('Based on:'))
    main_layout.addWidget(self.report_cb)
    main_layout.addWidget(QLabel('Protocol:'))
    main_layout.addWidget(self.protocol_cb)
    main_layout.addWidget(HSeparator())
    main_layout.addWidget(self.d3_opts_cb)
    main_layout.addLayout(h)
    main_layout.addStretch()
    main_layout.addLayout(tab_nav)

    self.setLayout(main_layout)

  def sigConnect(self):
    self.hidden_btn.clicked.connect(self.on_check)
    self.protocol_cb.activated[int].connect(self.on_protocol_changed)
    self.report_cb.activated[int].connect(self.on_report_changed)
    self.calc_btn.clicked.connect(self.on_calculate)
    self.ctx.app_data.modeValueChanged.connect(self.diameter_mode_handle)
    self.ctx.app_data.diametersUpdated.connect(self.update_values)
    self.ctx.app_data.ctdivsUpdated.connect(self.update_values)
    self.ctx.app_data.DLPValueChanged.connect(self.dlp_handle)
    self.ctx.app_data.imgChanged.connect(self.img_changed_handle)
    self.ctx.app_data.mode3dChanged.connect(self.mode3d_changed_handle)
    self.ctx.app_data.slice1Changed.connect(self.slice1_changed_handle)
    self.ctx.app_data.slice2Changed.connect(self.slice2_changed_handle)
    self.plot_chk.stateChanged.connect(self.on_show_graph_check)
    self.avg_chk.stateChanged.connect(self.on_avg_check)
    self.show_ssde_graph_chk.stateChanged.connect(self.on_show_ssde_graph_check)
    self.d3_opts_cb.activated[int].connect(self.on_mode_changed)
    [btn.toggled.connect(self.on_3d_opts_changed) for btn in self.d3opts_rbtns]

  def plot(self, data):
    x = self.diameter
    y = self.convf
    xlabel = 'Dw' if self.ctx.app_data.mode==DW else 'Deff'
    title = 'Water Equivalent Diameter' if self.ctx.app_data.mode==DW else 'Effective Diameter'
    self.figure = PlotDialog()
    self.figure.actionEnabled(True)
    self.figure.trendActionEnabled(False)
    self.figure.plot(data, pen={'color': "FFFF00", 'width': 2}, symbol=None)
    self.figure.plot([x], [y], symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
    self.figure.annotate('cf', pos=(x,y), text=f'{xlabel}: {x:#.2f} cm\nConv. Factor: {y:#.2f}', anchor=(0,1))
    self.figure.axes.showGrid(True,True)
    self.figure.setLabels(xlabel,'Conversion Factor','cm','')
    self.figure.setTitle(f'{title} - Conversion Factor')
    self.figure.show()

  def plot_ssde(self, idxs, ssdes):
    xlabel = 'SSDE'
    title = 'SSDE'
    self.figure_ssde = PlotDialog()
    self.figure_ssde.actionEnabled(True)
    self.figure_ssde.trendActionEnabled(False)
    self.figure_ssde.plot(idxs, ssdes, pen={'color': "FFFF00", 'width': 2}, symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
    self.figure_ssde.axes.showGrid(True,True)
    self.figure_ssde.setLabels('slice',xlabel,'','mGy')
    self.figure_ssde.setTitle(f'Slice - {title}')
    self.figure_ssde.show()

  def switch_button_default(self, mode=0):
    if mode==0:
      self.calc_btn.setAutoDefault(True)
      self.calc_btn.setDefault(True)
      self.save_btn.setAutoDefault(False)
      self.save_btn.setDefault(False)
    elif mode==1:
      self.save_btn.setAutoDefault(True)
      self.save_btn.setDefault(True)
      self.calc_btn.setAutoDefault(False)
      self.calc_btn.setDefault(False)
    else:
      return
    self.next_tab_btn.setAutoDefault(False)
    self.next_tab_btn.setDefault(False)
    self.prev_tab_btn.setAutoDefault(False)
    self.prev_tab_btn.setDefault(False)

  def diameter_mode_handle(self, value):
    self.current_dlabel = '<b>Dw (cm)</b>' if value == DW else '<b>Deff (cm)</b>'
    self.diameter_label.setText(self.current_dlabel)

  def diameter_handle(self, value):
    self.diameter_edit.setText(f'{value:#.2f}')

  def ctdiv_handle(self, value):
    self.ctdiv_edit.setText(f'{value:#.2f}')

  def dlp_handle(self, value):
    self.dlp_edit.setText(f'{value:#.2f}')

  def on_protocol_changed(self, idx):
    self.protocol_id = self.protocol_model.record(idx).value("id")
    self.alfa = self.effdose_model.record(self.protocol_id-1).value("alfaE")
    self.beta = self.effdose_model.record(self.protocol_id-1).value("betaE")

  def on_report_changed(self, idx):
    self.report_id = self.report_model.record(idx).value("id")
    self.cf_model.setFilter(f"report_id={self.report_id} AND phantom_id={self.ctx.phantom}")
    self.cf_model.select()

    a_val = self.cf_model.record(0).value("a")
    b_val = self.cf_model.record(0).value("b")
    self.cf_eq = lambda x: a_val*np.exp(-b_val*x)

  def on_show_graph_check(self, state):
    self.show_graph = state == Qt.Checked

  def on_avg_check(self, state):
    self.use_avg = state == Qt.Checked

  def on_show_ssde_graph_check(self, state):
    self.show_ssde_graph = state == Qt.Checked

  def mode3d_changed_handle(self, value):
    rb = [r for r in self.d3opts_rbtns if r.text().lower()==value]
    rb[0].setChecked(True)

  def slice1_changed_handle(self, value):
    self.slice1_sb.setValue(value)

  def slice2_changed_handle(self, value):
    self.slice2_sb.setValue(value)

  def on_3d_opts_changed(self, sel):
    sel = self.sender()
    if sel.isChecked():
      self.d3_method = sel.text().lower()
      if self.d3_method == 'regional':
        self.to_lbl.setHidden(False)
        self.slice2_sb.setHidden(False)
        self.slice1_sb.setMinimum(1)
        self.slice1_sb.setMaximum(self.ctx.total_img)
      else:
        self.to_lbl.setHidden(True)
        self.slice2_sb.setHidden(True)

  def on_mode_changed(self, idx):
    self.all_slices = idx==1
    label_d = self.current_dlabel[:3]+'Avg. '+self.current_dlabel[3:] if self.all_slices else self.current_dlabel
    label_c = '<b>Avg. CTDI<sub>vol</sub> (mGy)</b>' if self.all_slices else '<b>CTDI<sub>vol</sub> (mGy)</b>'
    label_s = '<b>Avg. SSDE (mGy)</b>' if self.all_slices else '<b>SSDE (mGy)</b>'
    self.diameter_label.setText(label_d)
    self.ctdiv_label.setText(label_c)
    self.ssde_label.setText(label_s)
    self.d3opts_grpbox.setVisible(self.all_slices)
    self.ctx.app_data.s_mode = idx
    self.update_values()

  def get_idxs(self):
    dcms = np.array(self.ctx.dicoms)
    index = list(range(len(dcms)))
    idxs = index
    if self.all_slices:
      nslice = self.slice1_sb.value()
      if self.d3_method  == 'slice step':
        idxs = index[::nslice]
      elif self.d3_method  == 'slice number':
        tmps = np.array_split(np.arange(len(dcms)), nslice)
        idxs = [tmp[len(tmp)//2] for tmp in tmps]
      elif self.d3_method  == 'regional':
        nslice2 = self.slice2_sb.value()
        first = nslice if nslice<=nslice2 else nslice2
        last = nslice2 if nslice<=nslice2 else nslice
        idxs = index[first-1:last]
    self.idxs = [idx+1 for idx in idxs]

  def on_calculate(self):
    try:
      self.ctx.app_data.convf = self.cf_eq(self.ctx.app_data.diameter)
    except:
      QMessageBox.warning(None, "No Data", f"There are no data in {self.report_cb.currentText()} report for {self.ctx.phantom_name} phantom.")
      return

    if not self.all_slices:
      if self.use_avg:
        self.ctx.app_data.SSDE = self.ctx.app_data.convf * self.ctx.app_data.CTDIv
      else:
        try:
          self.diameter = self.ctx.app_data.diameters[self.ctx.current_img]
          self.CTDIv = self.ctx.app_data.CTDIvs[self.ctx.current_img]
        except:
          QMessageBox.warning(None, "No Data", f"No CTDIv and diameter data for slice {self.ctx.current_img}.\nCalculate them first.")
          return
        self.convf = self.cf_eq(self.diameter)
        self.SSDE = self.convf * self.CTDIv
        self.DLPc = self.convf * self.ctx.app_data.DLP
        self.effdose = self.ctx.app_data.DLP * np.exp(self.alfa*self.diameter + self.beta)

        self.ctx.app_data.convfs[self.ctx.current_img] = self.convf
        self.ctx.app_data.SSDEs[self.ctx.current_img] = self.SSDE
        self.ctx.app_data.dlpcs[self.ctx.current_img] = self.DLPc
        self.ctx.app_data.effdoses[self.ctx.current_img] = self.effdose
        self.ctx.app_data.emit_s_changed()
    else:
      ctdivs = []
      diameters = []
      cond = self.d3_method==self.ctx.app_data.mode3d and self.slice1_sb.value()==self.ctx.app_data.slice1
      if self.d3_method=='regional':
        cond = cond and self.slice2_sb.value()==self.ctx.app_data.slice2
      self.get_idxs()
      idx_to_remove = []
      for idx in self.idxs:
        if idx not in self.ctx.app_data.CTDIvs.keys() or idx not in self.ctx.app_data.diameters.keys():
          idx_to_remove.append(idx)
          continue
        ctdivs.append(self.ctx.app_data.CTDIvs[idx])
        diameters.append(self.ctx.app_data.diameters[idx])

      if len(idx_to_remove)>0:
        [self.idxs.remove(idx) for idx in idx_to_remove if idx in self.idxs]

      self.ctdivs = np.array(ctdivs)
      self.diameters = np.array(diameters)
      convfs = self.cf_eq(self.diameters)
      self.ssdes = convfs * self.ctdivs
      dlpcs = convfs * self.ctx.app_data.DLP
      effdoses = self.ctx.app_data.DLP * np.exp(self.alfa*self.diameters + self.beta)

      self.diameter = self.diameters.mean()
      self.CTDIv = self.ctdivs.mean()
      self.SSDE = self.ssdes.mean()
      self.convf = self.cf_eq(self.diameter)
      self.DLPc = self.convf * self.ctx.app_data.DLP
      self.effdose = self.ctx.app_data.DLP * np.exp(self.alfa*self.diameter + self.beta)

      for idx, v in enumerate(self.idxs):
        self.ctx.app_data.convfs[v] = convfs[idx]
        self.ctx.app_data.SSDEs[v] = self.ssdes[idx]
        self.ctx.app_data.dlpcs[v] = dlpcs[idx]
        self.ctx.app_data.effdoses[v] = effdoses[idx]
      self.ctx.app_data.emit_s_changed()

      if self.show_ssde_graph:
        self.plot_ssde(self.idxs, self.ssdes)

    self.diameter_edit.setText(f'{self.diameter:#.2f}')
    self.ctdiv_edit.setText(f'{self.CTDIv:#.2f}')
    self.convf_edit.setText(f'{self.convf:#.2f}')
    self.ssde_edit.setText(f'{self.SSDE:#.2f}')
    self.dlpc_edit.setText(f'{self.DLPc:#.2f}')
    self.effdose_edit.setText(f'{self.effdose:#.2f}')

    self.ctx.app_data.effdose = self.effdose
    self.ctx.app_data.DLPc = self.DLPc

    self.set_data()

    if self.show_graph:
      minv = 6 if self.ctx.phantom == HEAD else 8
      maxv = 55 if self.ctx.phantom == HEAD else 45
      deff = np.arange(minv, maxv+1, 1)
      cf = self.cf_eq(deff)
      data = np.array([deff, cf]).T
      self.plot(data)

    self.switch_button_default(mode=1)

  def update_values(self, val=True):
    if not val:
      return
    try:
      self.CTDIv = self.ctx.app_data.CTDIvs[self.ctx.current_img] if not self.all_slices else self.ctdivs.mean()
    except:
      self.CTDIv = 0
    try:
      self.diameter = self.ctx.app_data.diameters[self.ctx.current_img] if not self.all_slices else self.diameters.mean()
    except:
      self.diameter = 0
    try:
      self.convf = self.ctx.app_data.convfs[self.ctx.current_img] if not self.all_slices else self.cf_eq(self.diameter)
    except:
      self.convf = 0
    try:
      self.SSDE = self.ctx.app_data.SSDEs[self.ctx.current_img] if not self.all_slices else self.ssdes.mean()
    except:
      self.SSDE = 0
    try:
      self.DLPc = self.ctx.app_data.dlpcs[self.ctx.current_img] if not self.all_slices else self.cf_eq(self.diameter) * self.ctx.app_data.DLP
    except:
      self.DLPc = 0
    try:
      self.effdose = self.ctx.app_data.effdoses[self.ctx.current_img] if not self.all_slices else self.ctx.app_data.DLP * np.exp(self.alfa*self.diameter + self.beta)
    except:
      self.effdose = 0
    self.convf_edit.setText(f'{self.convf:#.2f}')
    self.ctdiv_edit.setText(f'{self.CTDIv:#.2f}')
    self.diameter_edit.setText(f'{self.diameter:#.2f}')
    self.ssde_edit.setText(f'{self.SSDE:#.2f}')
    self.dlpc_edit.setText(f'{self.DLPc:#.2f}')
    self.effdose_edit.setText(f'{self.effdose:#.2f}')
    self.set_data()

  def img_changed_handle(self, value):
    if value:
      self.update_values()
      # self.reset_fields()

  def reset_fields(self):
    self.initVar()
    self.ctx.app_data.convf = 0
    self.ctx.app_data.SSDE = 0
    self.ctx.app_data.DLPc = 0
    self.ctx.app_data.effdose = 0
    self.show_graph = False
    self.use_avg = False
    self.d3_opts_cb.setCurrentIndex(0)
    self.on_mode_changed(0)
    self.plot_chk.setCheckState(Qt.Unchecked)
    self.avg_chk.setCheckState(Qt.Unchecked)
    self.switch_button_default()
    self.ctdiv_edit.setText(f'{0:#.2f}')
    self.diameter_edit.setText(f'{0:#.2f}')
    self.dlp_edit.setText(f'{0:#.2f}')
    self.convf_edit.setText(f'{0:#.2f}')
    self.ssde_edit.setText(f'{0:#.2f}')
    self.dlpc_edit.setText(f'{0:#.2f}')
    self.effdose_edit.setText(f'{0:#.2f}')

  def on_check(self):
    print('ctdi', self.ctx.app_data.CTDIvs)
    print('diameter', self.ctx.app_data.diameters)
    print('ssde', self.ctx.app_data.SSDEs)
