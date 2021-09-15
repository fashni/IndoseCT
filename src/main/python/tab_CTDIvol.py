import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator, QFont
from PyQt5.QtSql import QSqlTableModel
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QRadioButton, QSpacerItem, QSpinBox,
                             QStackedLayout, QVBoxLayout, QWidget)

from constants import *
from Plot import PlotDialog


class CTDIVolTab(QDialog):
  def __init__(self, ctx, *args, **kwargs):
    super(CTDIVolTab, self).__init__(*args, **kwargs)
    self.ctx = ctx
    self.prev_mode = 0
    self.method = 0
    self.calc_3d_method = 'slice step'
    self.dcm_3d_method = 'slice step'
    self.initVar()
    self.initModel()
    self.initUI()
    self.setModel()
    self.sigConnect()

  def initVar(self):
    self.CTDI = 0
    self.DLP = 0
    self.tube_current = 100
    self.rotation_time = 1
    self.pitch = 1
    self.coll = 0
    self.scan_length = 10
    self.mAs = 0
    self.eff_mAs = 0
    self.CTDIw = 0
    self.CTDIv = 0
    self.idxs = []
    self.currents = []
    self.ctdivs = []
    self.all_slices = False
    self.all_slices_dcm = False
    self.all_slices_man = False
    self.show_graph_ctd = False
    self.show_graph_tcm = False
    self.show_graph_ctd_dcm = False
    self.show_graph_tcm_dcm = False
    self.adjust_tcm = False
    self.disable_warning = False

  def initModel(self):
    self.brand_query = QSqlTableModel(db=self.ctx.database.ctdi_db)
    self.scanner_query = QSqlTableModel(db=self.ctx.database.ctdi_db)
    self.volt_query = QSqlTableModel(db=self.ctx.database.ctdi_db)
    self.coll_query = QSqlTableModel(db=self.ctx.database.ctdi_db)

    # fill brand combobox
    self.brand_query.setTable("BRAND")
    self.brand_query.select()
    self.brand_id = self.brand_query.record(0).value("ID")

    # fill scanner combobox
    self.scanner_query.setTable("SCANNER")
    self.scanner_query.setFilter("BRAND_ID=1")
    self.scanner_query.select()
    self.scanner_id = self.scanner_query.record(0).value("ID")

    # fill voltage combobox
    self.volt_query.setTable("CTDI_DATA")
    self.volt_query.setFilter("SCANNER_ID=1")
    self.volt_query.select()
    self.CTDI = self.volt_query.record(0).value("CTDI_HEAD")

    # fill collimation combobox
    self.coll_query.setTable("COLLIMATION_DATA")
    self.coll_query.setFilter("SCANNER_ID=1")
    self.coll_query.select()
    self.coll = self.coll_query.record(0).value("VALUE")

  def setModel(self):
    self.brand_cb.setModel(self.brand_query)
    self.brand_cb.setModelColumn(self.brand_query.fieldIndex("NAME"))
    self.scanner_cb.setModel(self.scanner_query)
    self.scanner_cb.setModelColumn(self.scanner_query.fieldIndex("NAME"))
    self.volt_cb.setModel(self.volt_query)
    self.volt_cb.setModelColumn(self.volt_query.fieldIndex("VOLTAGE"))
    self.coll_cb.setModel(self.coll_query)
    self.coll_cb.setModelColumn(self.coll_query.fieldIndex("COL_OPTS"))

    self.on_brand_changed(0)
    self.brand_items = [self.brand_cb.itemText(i).lower() for i in range(self.brand_cb.count())]

  def sigConnect(self):
    self.opts.activated[int].connect(self.on_set_method)
    self.brand_cb.activated[int].connect(self.on_brand_changed)
    self.scanner_cb.activated[int].connect(self.on_scanner_changed)
    self.volt_cb.activated[int].connect(self.on_volt_changed)
    self.coll_cb.activated[int].connect(self.on_coll_changed)
    self.tube_current_edit.textChanged[str].connect(self.on_tube_current_changed)
    self.rotation_time_edit.textChanged[str].connect(self.on_rotation_time_changed)
    self.pitch_edit.textChanged[str].connect(self.on_pitch_changed)
    self.scan_length_c_edit.textChanged[str].connect(self.on_scan_length_changed)
    self.ctdiv_m_edit.textChanged[str].connect(self.on_ctdiv_changed)
    self.dlp_m_edit.textChanged[str].connect(self.on_dlp_changed)
    # self.scan_length_d_edit.textChanged[str].connect(self.on_dicom_manual)
    # self.ctdiv_d_edit.textChanged[str].connect(self.on_dicom_manual)
    self.tcm_btn.clicked.connect(self.on_get_tcm)
    self.scn_btn.clicked.connect(self.get_scan_length_dicom)
    self.get_info_btn.clicked.connect(self.on_get_info)
    self.calc_btn.clicked.connect(self.calculate_method)
    self.calc_dcm_btn.clicked.connect(self.calculate_dcm)
    self.calc_man_btn.clicked.connect(self.calculate_man)
    self.ctx.app_data.imgChanged.connect(self.img_changed_handle)
    self.show_graph_ctd_chk.stateChanged.connect(self.on_show_graph_ctd_state)
    self.show_graph_tcm_chk.stateChanged.connect(self.on_show_graph_tcm_state)
    self.show_graph_ctd_dcm_chk.stateChanged.connect(self.on_show_graph_ctd_dcm_state)
    self.show_graph_tcm_dcm_chk.stateChanged.connect(self.on_show_graph_tcm_dcm_state)
    self.tcm_correction_chk.stateChanged.connect(self.on_tcm_correction_state)
    self.all_slices_man_chk.stateChanged.connect(self.on_mode_man_changed)
    self.mode_calc_cb.activated[int].connect(self.on_mode_calc_changed)
    self.mode_dcm_cb.activated[int].connect(self.on_mode_dcm_changed)
    [btn.toggled.connect(self.on_calc_3d_opts_changed) for btn in self.calc_d3opts_rbtns]
    [btn.toggled.connect(self.on_dcm_3d_opts_changed) for btn in self.dcm_d3opts_rbtns]

  def initUI(self):
    self.figure = PlotDialog()
    self.opts = QComboBox()
    self.opts.addItems(['Calculation', 'Get from DICOM', 'Input Manually'])

    self.brand_cb = QComboBox()
    self.scanner_cb = QComboBox()
    self.volt_cb = QComboBox()
    self.coll_cb = QComboBox()
    self.mode_calc_cb = QComboBox(self)
    self.mode_dcm_cb = QComboBox(self)

    self.mode_calc_cb.addItems(['One slice', 'Z-axis'])
    self.mode_dcm_cb.addItems(['One slice', 'Z-axis'])

    self.tube_current_edit = QLineEdit(f'{self.tube_current}')
    self.rotation_time_edit = QLineEdit(f'{self.rotation_time}')
    self.pitch_edit = QLineEdit(f'{self.pitch}')
    self.scan_length_c_edit = QLineEdit(f'{self.scan_length}')
    self.scan_length_d_edit = QLineEdit(f'{self.scan_length}')

    self.mas_edit = QLineEdit('0')
    self.mas_eff_edit = QLineEdit('0')
    self.ctdiw_edit = QLineEdit('0')
    self.ctdiv_c_edit = QLineEdit('0')
    self.ctdiv_m_edit = QLineEdit('0')
    self.ctdiv_d_edit = QLineEdit('0')
    self.dlp_c_edit = QLineEdit('0')
    self.dlp_m_edit = QLineEdit('0')
    self.dlp_d_edit = QLineEdit('0')

    self.ctdiv_d_label = QLabel('CTDI<sub>vol</sub> (mGy)')
    # self.ctdiv_d2_label = QLabel('CTDI<sub>vol</sub> (mGy)')

    self.get_info_btn = QPushButton('Get Info')
    self.calc_btn = QPushButton('Calculate')
    self.calc_dcm_btn = QPushButton('Calculate')
    self.calc_man_btn = QPushButton('Submit')
    self.tcm_btn = QPushButton('TCM')
    self.scn_btn = QPushButton('Scn Len')
    self.next_tab_btn = QPushButton('Next')
    self.prev_tab_btn = QPushButton('Previous')
    self.prev_tab_btn.setVisible(False)

    self.show_graph_tcm_chk = QCheckBox('Show mA Graph')
    self.show_graph_ctd_chk = QCheckBox('Show CTDIvol Graph')
    self.show_graph_tcm_dcm_chk = QCheckBox('Show mA Graph')
    self.show_graph_ctd_dcm_chk = QCheckBox('Show CTDIvol Graph')
    self.tcm_correction_chk = QCheckBox('Adjust CTDIvol with mA')
    self.all_slices_man_chk = QCheckBox('All Slices')

    self.calc_slice1_sb = QSpinBox()
    self.calc_slice2_sb = QSpinBox()
    self.calc_to_lbl = QLabel('to')
    self.calc_d3opts_rbtns = [QRadioButton('Slice Step'), QRadioButton('Slice Number'), QRadioButton('Regional')]
    self.calc_d3opts_rbtns[0].setChecked(True)

    self.dcm_slice1_sb = QSpinBox()
    self.dcm_slice2_sb = QSpinBox()
    self.dcm_to_lbl = QLabel('to')
    self.dcm_d3opts_rbtns = [QRadioButton('Slice Step'), QRadioButton('Slice Number'), QRadioButton('Regional')]
    self.dcm_d3opts_rbtns[0].setChecked(True)

    self.calc_slice1_sb.setMinimum(1)
    self.calc_slice1_sb.setMaximum(self.ctx.total_img)
    self.calc_slice1_sb.setMinimumWidth(50)
    self.calc_slice2_sb.setMinimum(1)
    self.calc_slice2_sb.setMaximum(self.ctx.total_img)
    self.calc_slice2_sb.setMinimumWidth(50)
    self.calc_to_lbl.setHidden(True)
    self.calc_slice2_sb.setHidden(True)
    self.dcm_slice1_sb.setMinimum(1)
    self.dcm_slice1_sb.setMaximum(self.ctx.total_img)
    self.dcm_slice1_sb.setMinimumWidth(50)
    self.dcm_slice2_sb.setMinimum(1)
    self.dcm_slice2_sb.setMaximum(self.ctx.total_img)
    self.dcm_slice2_sb.setMinimumWidth(50)
    self.dcm_to_lbl.setHidden(True)
    self.dcm_slice2_sb.setHidden(True)

    self.brand_cb.setPlaceholderText('[Unavailable]')
    self.scanner_cb.setPlaceholderText('[Unavailable]')
    self.volt_cb.setPlaceholderText('[Unavailable]')
    self.coll_cb.setPlaceholderText('[Unavailable]')

    cbs = [
      self.brand_cb,
      self.scanner_cb,
      self.volt_cb,
      self.coll_cb,
      self.mode_calc_cb,
      self.mode_dcm_cb
    ]

    edits = [
      self.tube_current_edit,
      self.rotation_time_edit,
      self.pitch_edit,
      self.scan_length_c_edit,
      self.scan_length_d_edit,
      self.mas_edit,
      self.mas_eff_edit,
      self.ctdiw_edit,
      self.ctdiv_c_edit,
      self.ctdiv_m_edit,
      self.ctdiv_d_edit,
      self.dlp_c_edit,
      self.dlp_m_edit,
      self.dlp_d_edit,
    ]

    [edit.setValidator(QDoubleValidator()) for edit in edits]
    [edit.setMinimumWidth(100) for edit in edits]
    [edit.setMinimumWidth(100) for edit in cbs]
    [edit.setAlignment(Qt.AlignRight) for edit in edits]

    self.mas_edit.setReadOnly(True)
    self.mas_eff_edit.setReadOnly(True)
    self.ctdiw_edit.setReadOnly(True)
    self.ctdiv_c_edit.setReadOnly(True)
    self.dlp_c_edit.setReadOnly(True)

    self.switch_button_default()
    self.set_layout()

  def set_layout(self):
    font = QFont()
    font.setBold(True)
    self.ctdiv_c_edit.setFont(font)
    self.dlp_c_edit.setFont(font)

    manual_grpbox = QGroupBox('')
    manual_layout = QFormLayout()
    manual_layout.addRow(QLabel('CTDI<sub>vol</sub> (mGy)'), self.ctdiv_m_edit)
    manual_layout.addRow(QLabel('DLP (mGy-cm))'), self.dlp_m_edit)
    manual_layout.addRow(self.calc_man_btn, QLabel(''))
    manual_layout.addRow(self.all_slices_man_chk, QLabel(''))
    manual_grpbox.setLayout(manual_layout)
    manual_grpbox.setFont(font)

    dcm_slice_layout = QHBoxLayout()
    dcm_slice_layout.addWidget(self.dcm_slice1_sb)
    dcm_slice_layout.addWidget(self.dcm_to_lbl)
    dcm_slice_layout.addWidget(self.dcm_slice2_sb)
    dcm_slice_layout.addStretch()

    self.dcm_d3opts_grpbox = QGroupBox('Z-axis Options')
    dcm_d3opts_layout = QVBoxLayout()
    [dcm_d3opts_layout.addWidget(btn) for btn in self.dcm_d3opts_rbtns]
    dcm_d3opts_layout.addLayout(dcm_slice_layout)
    dcm_d3opts_layout.addWidget(self.show_graph_ctd_dcm_chk)
    dcm_d3opts_layout.addWidget(self.show_graph_tcm_dcm_chk)
    dcm_d3opts_layout.addStretch()
    self.dcm_d3opts_grpbox.setLayout(dcm_d3opts_layout)
    self.dcm_d3opts_grpbox.setVisible(False)

    dicom_grpbox = QGroupBox('Parameter')
    dicom_layout = QFormLayout()
    dicom_layout.addRow(QLabel('Scan Length (cm)'), self.scan_length_d_edit)
    dicom_layout.addRow(self.ctdiv_d_label, self.ctdiv_d_edit)
    dicom_layout.addRow(QLabel('DLP (mGy-cm)'), self.dlp_d_edit)
    # dicom_layout.addRow(QLabel('Option'), self.mode_dcm_cb)
    dicom_layout.addRow(self.calc_dcm_btn, self.tcm_correction_chk)
    dicom_grpbox.setLayout(dicom_layout)
    # dicom_grpbox.setFont(font)

    dcm_widget = QWidget(self)
    dcm_layout = QHBoxLayout()
    dcm_layout.addWidget(dicom_grpbox)
    dcm_layout.addWidget(self.dcm_d3opts_grpbox)
    dcm_layout.setContentsMargins(0,0,0,0)
    dcm_widget.setLayout(dcm_layout)

    calc_btn_layout = QHBoxLayout()
    calc_btn_layout.addWidget(self.calc_btn)
    calc_btn_layout.addWidget(self.get_info_btn)

    calci_grpbox = QGroupBox('Parameter')
    calci_outer_layout = QVBoxLayout()
    calci_inner_layout = QFormLayout()
    calci_inner_layout.addRow(QLabel('Manufacturer'), self.brand_cb)
    calci_inner_layout.addRow(QLabel('Scanner'), self.scanner_cb)
    calci_inner_layout.addRow(QLabel('Voltage (kV)'), self.volt_cb)
    calci_inner_layout.addRow(QLabel('Tube Current (mA)'), self.tube_current_edit)
    calci_inner_layout.addRow(QLabel('Rotation Time (s)'), self.rotation_time_edit)
    calci_inner_layout.addRow(QLabel('Pitch'), self.pitch_edit)
    calci_inner_layout.addRow(QLabel('Collimation (mm)'), self.coll_cb)
    calci_inner_layout.addRow(QLabel('Scan Length (cm)'), self.scan_length_c_edit)
    # calci_inner_layout.addRow(QLabel('Option'), self.mode_calc_cb)
    calci_outer_layout.addLayout(calci_inner_layout)
    calci_outer_layout.addSpacerItem(QSpacerItem(1,10))
    calci_outer_layout.addLayout(calc_btn_layout)
    calci_outer_layout.addStretch()
    calci_grpbox.setLayout(calci_outer_layout)

    calco_grpbox = QGroupBox('Output')
    calco_layout = QFormLayout()
    calco_layout.addRow(QLabel('mAs'), self.mas_edit)
    calco_layout.addRow(QLabel('Effective mAs'), self.mas_eff_edit)
    calco_layout.addRow(QLabel('CTDI<sub>w</sub> (mGy)'), self.ctdiw_edit)
    calco_layout.addRow(QLabel('<b>CTDI<sub>vol</sub> (mGy)</b>'), self.ctdiv_c_edit)
    calco_layout.addRow(QLabel('<b>DLP (mGy-cm)</b>'), self.dlp_c_edit)
    calco_layout.setContentsMargins(11,3,11,3)
    calco_layout.setVerticalSpacing(5)
    calco_grpbox.setLayout(calco_layout)
    # print(calco_layout.verticalSpacing())

    calc_slice_layout = QHBoxLayout()
    calc_slice_layout.addWidget(self.calc_slice1_sb)
    calc_slice_layout.addWidget(self.calc_to_lbl)
    calc_slice_layout.addWidget(self.calc_slice2_sb)
    calc_slice_layout.addStretch()
    calc_chk_layout = QVBoxLayout()
    calc_chk_layout.addWidget(self.show_graph_ctd_chk)
    calc_chk_layout.addWidget(self.show_graph_tcm_chk)
    calc_chk_layout.setSpacing(3)
    calc_radio_layout = QVBoxLayout()
    [calc_radio_layout.addWidget(btn) for btn in self.calc_d3opts_rbtns]
    calc_radio_layout.setSpacing(3)

    self.calc_d3opts_grpbox = QGroupBox('Z-axis Options')
    calc_d3opts_layout = QVBoxLayout()
    calc_d3opts_layout.addLayout(calc_radio_layout)
    calc_d3opts_layout.addLayout(calc_slice_layout)
    calc_d3opts_layout.addLayout(calc_chk_layout)
    calc_d3opts_layout.addStretch()
    calc_d3opts_layout.setContentsMargins(11,3,11,3)
    calc_d3opts_layout.setSpacing(0)
    self.calc_d3opts_grpbox.setLayout(calc_d3opts_layout)
    self.calc_d3opts_grpbox.setVisible(False)

    calcr_layout = QVBoxLayout()
    calcr_layout.addWidget(calco_grpbox)
    calcr_layout.addWidget(self.calc_d3opts_grpbox)
    calcr_layout.setSpacing(0)
    # calcr_layout.addWidget(self.calc_graph_opts_grpbox)
    calcr_layout.addStretch()

    calc_widget = QWidget(self)
    calc_layout = QHBoxLayout()
    calc_layout.addWidget(calci_grpbox)
    calc_layout.addLayout(calcr_layout)
    calc_layout.setContentsMargins(0,0,0,0)
    calc_widget.setLayout(calc_layout)

    self.stacks = QStackedLayout()
    self.stacks.addWidget(calc_widget)
    self.stacks.addWidget(dcm_widget)
    self.stacks.addWidget(manual_grpbox)

    self.emp = QLabel('')
    self.stackz = QStackedLayout()
    self.stackz.addWidget(self.mode_calc_cb)
    self.stackz.addWidget(self.mode_dcm_cb)
    self.stackz.addWidget(self.emp)
    self.emp.setVisible(False)


    tab_nav = QHBoxLayout()
    tab_nav.addWidget(self.prev_tab_btn)
    tab_nav.addStretch()
    tab_nav.addWidget(self.next_tab_btn)

    main_layout = QVBoxLayout()
    main_layout.addWidget(QLabel('Methods:'))
    main_layout.addWidget(self.opts)
    main_layout.addLayout(self.stackz)
    main_layout.addStretch()
    main_layout.addLayout(self.stacks)
    main_layout.addStretch()
    main_layout.addLayout(tab_nav)

    self.setLayout(main_layout)

  def switch_button_default(self, method=0):
    if method==0:
      if self.method == 0:
        self.calc_btn.setAutoDefault(True)
        self.calc_btn.setDefault(True)
        self.calc_dcm_btn.setAutoDefault(False)
        self.calc_dcm_btn.setDefault(False)
      elif self.method == 1:
        self.calc_dcm_btn.setAutoDefault(True)
        self.calc_dcm_btn.setDefault(True)
        self.calc_btn.setAutoDefault(False)
        self.calc_btn.setDefault(False)
      self.next_tab_btn.setAutoDefault(False)
      self.next_tab_btn.setDefault(False)
    elif method==1:
      self.next_tab_btn.setAutoDefault(True)
      self.next_tab_btn.setDefault(True)
      self.calc_btn.setAutoDefault(False)
      self.calc_btn.setDefault(False)
      self.calc_dcm_btn.setAutoDefault(False)
      self.calc_dcm_btn.setDefault(False)
    else:
      return
    self.prev_tab_btn.setAutoDefault(False)
    self.prev_tab_btn.setDefault(False)
    self.tcm_btn.setAutoDefault(False)
    self.tcm_btn.setDefault(False)
    self.scn_btn.setAutoDefault(False)
    self.scn_btn.setDefault(False)
    self.get_info_btn.setAutoDefault(False)
    self.get_info_btn.setDefault(False)

  def plot_ctdiv(self):
    xlabel = 'CTDIvol'
    title = 'CTDIvol'
    self.figure_ctdi = PlotDialog()
    self.figure_ctdi.actionEnabled(True)
    self.figure_ctdi.trendActionEnabled(False)
    self.figure_ctdi.plot(self.idxs, self.ctdivs, pen={'color': "FFFF00", 'width': 2}, symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
    self.figure_ctdi.axes.showGrid(True,True)
    self.figure_ctdi.setLabels('slice',xlabel,'','mGy')
    self.figure_ctdi.setTitle(f'Slice - {title}')
    self.figure_ctdi.show()

  def plot_tcm(self):
    xlabel = 'Tube Current'
    title = 'Tube Current'
    self.figure = PlotDialog()
    self.figure.actionEnabled(True)
    self.figure.trendActionEnabled(False)
    self.figure.plot(self.idxs, self.currents, pen={'color': "FFFF00", 'width': 2}, symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
    self.figure.axes.showGrid(True,True)
    self.figure.setLabels('slice',xlabel,'','mA')
    self.figure.setTitle(f'Slice - {title}')
    self.figure.show()

  def on_get_tcm(self):
    if not self.ctx.isImage and not self.disable_warning:
      QMessageBox.warning(None, "Warning", "Open DICOM files first, or input manually")
      self.opts.setCurrentIndex(0)
      return
    self.currents = []
    self.idxs = []
    try:
      for idx, dcm in enumerate(self.ctx.dicoms):
        self.currents.append(float(dcm.XRayTubeCurrent))
        self.idxs.append(idx+1)
    except Exception as e:
      self.currents = []
      self.idxs = []
      if not self.disable_warning:
        QMessageBox.warning(None, 'Exception Occured', str(e))
      return
    tube_current = sum(self.currents)/self.ctx.total_img
    self.tube_current_edit.setText(f'{tube_current:#.2f}')
    self.tube_current = tube_current
    self.plot_tcm()

  def get_ctdiv_dicom(self, idx):
    try:
      ctdiv = float(self.ctx.dicoms[idx-1].CTDIvol)
    except:
      if not self.disable_warning:
        QMessageBox.warning(None, "Warning", "The DICOM does not contain the value of CTDIvol.\nPlease try different method.")
      ctdiv = 0
    return ctdiv

  def get_ctdiv_dicom_3d(self, idxs, dss):
    ctdivs = []
    currents = []
    to_remove = []
    for idx, dcm in zip(idxs, dss):
      if not hasattr(dcm, 'CTDIvol') or not hasattr(dcm, 'XRayTubeCurrent'):
        to_remove.append(idx)
        continue
      ctdivs.append(float(dcm.CTDIvol))
      currents.append(float(dcm.XRayTubeCurrent))

    if len(to_remove) > 0:
      [idxs.remove(idx) for idx in to_remove if idx in idxs]
    self.currents = np.array(currents)
    self.ctdivs = np.array(ctdivs)
    return idxs

  def get_scan_length_dicom(self):
    if self.method == 0 and not self.ctx.isImage and not self.disable_warning:
      QMessageBox.warning(None, "Warning", "Open DICOM files first, or input manually")
      self.opts.setCurrentIndex(0)
      return
    try:
      first = float(self.ctx.dicoms[0].SliceLocation)
      last = float(self.ctx.dicoms[-1].SliceLocation)
      width = float(self.ctx.dicoms[0].SliceThickness)
      try:
        second = float(self.ctx.dicoms[1].SliceLocation)
      except:
        second = last
    except Exception as e:
      if not self.disable_warning:
        QMessageBox.warning(None, 'Exception Occured', str(e))
      return

    lf = abs(0.1*(last-first))
    sf = abs(0.1*(second-first))
    print(lf, sf, width/10)
    scan_length = (abs((last-first)) + abs((second-first)) + width)*.1
    self.scan_length = scan_length
    if self.method == 0:
      self.scan_length_c_edit.setText(f'{self.scan_length:#.2f}')

  def on_get_info(self):
    if not self.ctx.isImage:
      QMessageBox.warning(None, "Warning", "Open DICOM files first, or input manually")
      return

    def find_closest_value(array, number):
      return min(array, key=lambda x:abs(x-number))

    attrs = ['Manufacturer', 'ManufacturerModelName', 'KVP', 'XRayTubeCurrent', 'ExposureTime', 'SpiralPitchFactor', 'TotalCollimationWidth']
    kv_pairs = {}
    missing_data = {}
    missing_attr = []
    for attr in attrs:
      try:
        kv_pairs[attr] = self.ctx.dicoms[self.ctx.current_img-1][attr].value
      except KeyError:
        kv_pairs[attr] = 0
        missing_attr.append(attr)

    if kv_pairs[attrs[0]].lower() in self.brand_items:
      brand_id = self.brand_items.index(kv_pairs[attrs[0]].lower())
      self.brand_cb.setCurrentIndex(brand_id)
      self.on_brand_changed(brand_id)
      if kv_pairs[attrs[1]].lower() in self.scanner_items:
        scanner_id = self.scanner_items.index(kv_pairs[attrs[1]].lower())
        self.scanner_cb.setCurrentIndex(scanner_id)
        self.on_scanner_changed(scanner_id)
        volt_id = self.volt_items.index(find_closest_value(self.volt_items, kv_pairs[attrs[2]]))
        coll_id = self.coll_items.index(find_closest_value(self.coll_items, kv_pairs[attrs[6]]))
        self.volt_cb.setCurrentIndex(volt_id)
        self.on_volt_changed(volt_id)
        self.coll_cb.setCurrentIndex(coll_id)
        self.on_coll_changed(coll_id)
      else:
        missing_data[attrs[1]] = kv_pairs[attrs[1]]
    else:
      missing_data[attrs[0]] = kv_pairs[attrs[0]]

    self.tube_current_edit.setText(f"{kv_pairs['XRayTubeCurrent']:#.2f}")
    self.rotation_time_edit.setText(f"{kv_pairs['ExposureTime']/1000:#.2f}")
    self.pitch_edit.setText(f"{kv_pairs['SpiralPitchFactor']:#.2f}")
    self.get_scan_length_dicom()

    if missing_attr:
      QMessageBox.information(None, 'Missing Attribute', f"The image has no attribute '{', '.join(missing_attr)}'.\nPlease input them manually.")
    if missing_data:
      QMessageBox.information(None, 'No Data', f"Data for '{list(missing_data.keys())[0]}: {list(missing_data.values())[0]}' is unavailable.")

  def on_set_method(self, idx):
    self.disable_warning = False
    self.prev_mode = self.method
    self.method = idx
    self.stacks.setCurrentIndex(idx)
    self.stackz.setCurrentIndex(idx)
    if self.method == 2:
      pass
      # self.calculate()
    elif self.method == 0:
      self.on_mode_calc_changed(self.mode_calc_cb.currentIndex())
    elif self.method == 1:
      self.on_mode_dcm_changed(self.mode_dcm_cb.currentIndex())

  def on_brand_changed(self, sel):
    self.brand_id = self.brand_query.record(sel).value("ID")

    self.scanner_query.setFilter(f"BRAND_ID={self.brand_id}")
    self.on_scanner_changed(0)
    self.scanner_items = [self.scanner_cb.itemText(i).lower() for i in range(self.scanner_cb.count())]

  def on_scanner_changed(self, sel):
    self.scanner_id = self.scanner_query.record(sel).value("ID")

    self.volt_query.setFilter(f"SCANNER_ID={self.scanner_id}")
    self.coll_query.setFilter(f"SCANNER_ID={self.scanner_id}")
    if self.volt_cb.count() == 0:
      QMessageBox.warning(None, 'No Data', f'There is no CTDI data for this scanner.')
    if self.coll_cb.count() == 0:
      QMessageBox.warning(None, 'No Data', 'There is no collimation data for this scanner.')
    self.on_volt_changed(0)
    self.on_coll_changed(0)
    self.volt_items = [float(self.volt_cb.itemText(i)) for i in range(self.volt_cb.count())]
    self.coll_items = [float(self.coll_query.record(i).value("COL_VAL")) for i in range(self.coll_cb.count())]

  def on_volt_changed(self, sel):
    phantom = 'head' if self.ctx.phantom==HEAD else 'body'
    self.CTDI = self.volt_query.record(sel).value(f"CTDI_{phantom.upper()}")
    if not self.CTDI and self.volt_cb.count() != 0:
      QMessageBox.warning(None, 'No Data', f'There is no {phantom.capitalize()} CTDI value for this voltage value.')
    # self.calculate(False)

  def on_coll_changed(self, sel):
    self.coll = self.coll_query.record(sel).value("VALUE")
    if not self.coll and self.coll_cb.count() != 0:
      QMessageBox.warning(None, 'No Data', 'There is no collimation data for this option.')
    # self.calculate(False)

  def on_tube_current_changed(self, sel):
    try:
      self.tube_current = float(sel)
    except ValueError:
      self.tube_current = 0
    # self.calculate(False)

  def on_rotation_time_changed(self, sel):
    try:
      self.rotation_time = float(sel)
    except ValueError:
      self.rotation_time = 1
    # self.calculate(False)

  def on_pitch_changed(self, sel):
    try:
      self.pitch = float(sel)
    except ValueError:
      self.pitch = 1
    # self.calculate(False)

  def on_scan_length_changed(self, sel):
    try:
      self.scan_length = float(sel)
    except ValueError:
      self.scan_length = 0
    # self.calculate(False)

  def on_dlp_changed(self, sel):
    try:
      self.DLP = float(sel)
    except ValueError:
      self.DLP = 0
    self.set_app_data()

  def on_ctdiv_changed(self, sel):
    try:
      self.CTDIv = float(sel)
    except ValueError:
      self.CTDIv = 0
    self.set_app_data()

  def on_dicom_manual(self):
    try:
      self.CTDIv = float(self.ctdiv_d_edit.text())
    except:
      self.CTDIv = 0
    try:
      self.scan_length = float(self.scan_length_d_edit.text())
    except:
      self.scan_length = 0
    self.DLP = self.CTDIv*self.scan_length
    self.dlp_d_edit.setText(f'{self.DLP:#.2f}')

  def img_changed_handle(self, value):
    if value:
      self.switch_button_default()

  def on_mode_man_changed(self, state):
    self.all_slices_man = state==Qt.Checked

  def on_mode_dcm_changed(self, idx):
    self.all_slices_dcm = idx==1
    if self.all_slices_dcm:
      self.ctdiv_d_label.setText("Avg. CTDI<sub>vol</sub> (mGy)")
    else:
      self.ctdiv_d_label.setText("CTDI<sub>vol</sub> (mGy)")
    self.show_graph_tcm_dcm_chk.setCheckState(Qt.Unchecked)
    self.show_graph_ctd_dcm_chk.setCheckState(Qt.Unchecked)
    self.dcm_d3opts_grpbox.setVisible(self.all_slices_dcm)
    self.show_graph_tcm_dcm = False
    self.show_graph_ctd_dcm = False
    self.ctx.app_data.c_mode = idx
    self.reset_dcm()
    self.mode_calc_cb.setCurrentIndex(idx)

  def on_mode_calc_changed(self, idx):
    self.all_slices = idx==1
    self.show_graph_tcm_chk.setCheckState(Qt.Unchecked)
    self.show_graph_ctd_chk.setCheckState(Qt.Unchecked)
    self.calc_d3opts_grpbox.setVisible(self.all_slices)
    self.show_graph_tcm = False
    self.show_graph_ctd = False
    self.ctx.app_data.c_mode = idx
    self.mode_dcm_cb.setCurrentIndex(idx)

  def on_show_graph_ctd_state(self, state):
    self.show_graph_ctd = state == Qt.Checked

  def on_show_graph_tcm_state(self, state):
    self.show_graph_tcm = state == Qt.Checked

  def on_show_graph_ctd_dcm_state(self, state):
    self.show_graph_ctd_dcm = state == Qt.Checked

  def on_show_graph_tcm_dcm_state(self, state):
    self.show_graph_tcm_dcm = state == Qt.Checked

  def on_tcm_correction_state(self, state):
    self.adjust_tcm = state == Qt.Checked

  def on_calc_3d_opts_changed(self, sel):
    sel = self.sender()
    if sel.isChecked():
      self.calc_3d_method = sel.text().lower()
      if self.calc_3d_method == 'regional':
        self.calc_to_lbl.setHidden(False)
        self.calc_slice2_sb.setHidden(False)
        self.calc_slice1_sb.setMinimum(1)
        self.calc_slice1_sb.setMaximum(self.ctx.total_img)
      else:
        self.calc_to_lbl.setHidden(True)
        self.calc_slice2_sb.setHidden(True)

  def on_dcm_3d_opts_changed(self, sel):
    sel = self.sender()
    if sel.isChecked():
      self.dcm_3d_method = sel.text().lower()
      if self.dcm_3d_method == 'regional':
        self.dcm_to_lbl.setHidden(False)
        self.dcm_slice2_sb.setHidden(False)
        self.dcm_slice1_sb.setMinimum(1)
        self.dcm_slice1_sb.setMaximum(self.ctx.total_img)
      else:
        self.dcm_to_lbl.setHidden(True)
        self.dcm_slice2_sb.setHidden(True)

  def calc_all_slices(self, idxs, dss):
    if not self.ctx.isImage:
      QMessageBox.warning(None, "Warning", "Open DICOM files first.")
      return
    c = []
    e = []
    to_remove = []
    for idx, dcm in zip(idxs, dss):
      if not hasattr(dcm, 'XRayTubeCurrent') or not hasattr(dcm, 'ExposureTime'):
        to_remove.append(idx)
        continue
      c.append(float(dcm.XRayTubeCurrent))
      e.append(float(dcm.ExposureTime)/1000)
    if len(to_remove)>0:
      [idxs.remove(idx) for idx in to_remove if idx in idxs]

    currents = np.array(c)
    exp_time = np.array(e)
    mAs = currents*exp_time
    eff_mAs = mAs/self.pitch if self.pitch > 0 else mAs
    ctdiw = self.coll*self.CTDI*mAs / 100
    ctdiv = ctdiw/self.pitch
      # print(idx+1, currents[idx], exp_time[idx], mAs[idx], eff_mAs[idx], ctdiw[idx], ctdiv[idx], sep='\t')

    self.currents = currents
    self.ctdivs = ctdiv
    # self.idxs = np.arange(1, self.ctx.total_img+1, dtype=int)

    self.tube_current_edit.setText(f"{currents.mean():#.2f}")
    self.rotation_time_edit.setText(f"{exp_time.mean():#.2f}")
    self.mAs = mAs.mean()
    self.eff_mAs = eff_mAs.mean()
    self.CTDIw = ctdiw.mean()
    self.CTDIv = ctdiv.mean()
    return idxs

  def calculate_method(self):
    if not self.all_slices:
      self.mAs = self.tube_current*self.rotation_time
      try:
        self.eff_mAs = self.mAs/self.pitch
      except ZeroDivisionError:
        self.eff_mAs = self.mAs
      try:
        self.CTDIw = self.coll*self.CTDI*self.mAs / 100
      except TypeError:
        self.CTDIw = 0
      try:
        # self.CTDIv = self.coll*self.CTDI*self.eff_mAs / 100
        self.CTDIv = self.CTDIw / self.pitch
      except:
        self.CTDIv = 0
      self.ctx.app_data.CTDIvs[self.ctx.current_img] = self.CTDIv
      self.ctx.app_data.emit_c_changed()
    else:
      self.idxs = []
      nslice = self.calc_slice1_sb.value()
      dcms = np.array(self.ctx.dicoms)
      index = list(range(len(dcms)))
      self.ctx.app_data.mode3d = self.calc_3d_method
      self.ctx.app_data.slice1 = nslice
      if self.calc_3d_method  == 'slice step':
        idxs = index[::nslice]
        imgs = dcms[::nslice]
      elif self.calc_3d_method  == 'slice number':
        tmps = np.array_split(np.arange(len(dcms)), nslice)
        idxs = [tmp[len(tmp)//2] for tmp in tmps]
        imgs = dcms[idxs]
      elif self.calc_3d_method  == 'regional':
        nslice2 = self.calc_slice2_sb.value()
        self.ctx.app_data.slice2 = nslice2
        first = nslice if nslice<=nslice2 else nslice2
        last = nslice2 if nslice<=nslice2 else nslice
        idxs = index[first-1:last]
        imgs = dcms[first-1:last]
      else:
        imgs = dcms
        idxs = index
      idxs = self.calc_all_slices(idxs, imgs)
      self.idxs = [i+1 for i in idxs]
      for k, v in zip(self.idxs, self.ctdivs):
        self.ctx.app_data.CTDIvs[k] = v
      self.ctx.app_data.emit_c_changed()

    self.DLP = self.CTDIv*self.scan_length
    self.mas_edit.setText(f'{self.mAs:#.2f}')
    self.mas_eff_edit.setText(f'{self.eff_mAs:#.2f}')
    self.ctdiw_edit.setText(f'{self.CTDIw:#.2f}')
    self.ctdiv_c_edit.setText(f'{self.CTDIv:#.2f}')
    self.dlp_c_edit.setText(f'{self.DLP:#.2f}')

    self.ctx.app_data.CTDIv = self.CTDIv
    self.ctx.app_data.DLP = self.DLP

    if self.show_graph_tcm:
      self.plot_tcm()
    if self.show_graph_ctd:
      self.plot_ctdiv()

    self.switch_button_default(method=1)

  def calculate_dcm(self):
    self.idxs = []
    if not self.ctx.isImage and not self.disable_warning:
      QMessageBox.warning(None, "Warning", "Open DICOM files first.")
      return

    self.get_scan_length_dicom()
    # curCTDIv = self.get_ctdiv_dicom(self.ctx.current_img)
    dcms = np.array(self.ctx.dicoms)
    index = list(range(len(dcms)))
    index = self.get_ctdiv_dicom_3d(index, dcms)
    if self.all_slices_dcm:
      nslice = self.dcm_slice1_sb.value()
      self.ctx.app_data.mode3d = self.dcm_3d_method
      self.ctx.app_data.slice1 = nslice
      if self.dcm_3d_method  == 'slice step':
        idxs = index[::nslice]
        imgs = dcms[::nslice]
      elif self.dcm_3d_method  == 'slice number':
        tmps = np.array_split(np.arange(len(dcms)), nslice)
        idxs = [tmp[len(tmp)//2] for tmp in tmps]
        imgs = dcms[idxs]
      elif self.dcm_3d_method  == 'regional':
        nslice2 = self.dcm_slice2_sb.value()
        self.ctx.app_data.slice2 = nslice2
        first = nslice if nslice<=nslice2 else nslice2
        last = nslice2 if nslice<=nslice2 else nslice
        idxs = index[first-1:last]
        imgs = dcms[first-1:last]
      else:
        imgs = dcms
        idxs = index
    else:
      imgs = dcms
      idxs = index

    if self.adjust_tcm:
      self.ctdivs = (self.ctdivs * self.currents) / self.currents.mean()

    self.ctdivs = self.ctdivs[idxs]
    self.CTDIv = self.ctdivs.mean()
    curidx = idxs.index(self.ctx.current_img-1) if self.ctx.current_img-1 in idxs else None
    if self.all_slices_dcm:
      ctdi = self.CTDIv
    else:
      ctdi = self.ctdivs[curidx] if curidx is not None else 0
    scan_length = self.scan_length
    DLP = ctdi*scan_length

    self.ctdiv_d_edit.setText(f'{ctdi:#.2f}')
    self.scan_length_d_edit.setText(f'{scan_length:#.2f}')
    self.dlp_d_edit.setText(f'{DLP:#.2f}')

    self.CTDIv = ctdi
    self.scan_length = scan_length
    self.DLP = DLP

    if self.all_slices_dcm:
      self.idxs = [i+1 for i in idxs]
      for k, v in zip(self.idxs, self.ctdivs):
        self.ctx.app_data.CTDIvs[k] = v
    else:
      self.ctx.app_data.CTDIvs[self.ctx.current_img] = ctdi
    self.ctx.app_data.emit_c_changed()
    self.ctx.app_data.CTDIv = self.CTDIv
    self.ctx.app_data.DLP = self.DLP

    if self.show_graph_ctd_dcm:
      self.plot_ctdiv()
    if self.show_graph_tcm_dcm:
      self.plot_tcm()
    self.switch_button_default(method=1)

  def calculate_man(self):
    try:
      ctdi = float(self.ctdiv_m_edit.text())
    except:
      ctdi = 0
    try:
      self.DLP = float(self.dlp_m_edit.text())
    except:
      self.DLP = 0
    if self.ctx.total_img < 1:
      return
    if self.all_slices_man:
      for idx in range(1, self.ctx.total_img+1):
        self.ctx.app_data.CTDIvs[idx] = ctdi
    else:
      self.ctx.app_data.CTDIvs[self.ctx.current_img] = ctdi
    self.ctx.app_data.DLP = self.DLP

  def calculate(self, auto=True):
    if self.method == 2:
      self.ctx.app_data.c_mode = 0
      try:
        self.CTDIv = float(self.ctdiv_m_edit.text())
      except:
        self.CTDIv = 0
      try:
        self.DLP = float(self.dlp_m_edit.text())
      except:
        self.DLP = 0
      self.idxs = range(1, self.ctx.total_img+1)
      self.ctdivs = [self.CTDIv for _ in self.idxs]
      self.ctx.app_data.CTDIv = self.CTDIv
      self.ctx.app_data.DLP = self.DLP

    self.switch_button_default(method=1)

  def set_app_data(self):
    self.ctx.app_data.CTDIv = self.CTDIv
    self.ctx.app_data.DLP = self.DLP

  def reset_dcm(self):
    self.scan_length = 10
    self.scan_length_d_edit.setText(f"{self.scan_length}")
    self.ctdivs = []
    self.CTDIv = 0
    self.DLP = 0
    self.ctdiv_d_edit.setText(f"{self.CTDIv}")
    self.dlp_d_edit.setText(f"{self.DLP}")

  def reset_fields(self):
    self.initVar()
    self.switch_button_default()
    self.disable_warning = True
    if self.method == 0:
      self.brand_cb.setCurrentIndex(0)
      self.scanner_cb.setCurrentIndex(0)
      self.volt_cb.setCurrentIndex(0)
      self.coll_cb.setCurrentIndex(0)
      self.on_brand_changed(0)
      self.mode_calc_cb.setCurrentIndex(0)
      self.on_mode_calc_changed(0)
    elif self.method == 1:
      self.reset_dcm()
      self.mode_dcm_cb.setCurrentIndex(0)
      self.on_mode_dcm_changed(0)
    else:
      self.ctdiv_m_edit.setText('0')
      self.dlp_m_edit.setText('0')
    self.all_slices_man_chk.setChecked(False)
    self.tube_current_edit.setText(f'{self.tube_current:#.2f}')
    self.rotation_time_edit.setText(f'{self.rotation_time:#.2f}')
    self.pitch_edit.setText(f'{self.pitch:#.2f}')
    self.scan_length_c_edit.setText(f'{self.scan_length:#.2f}')
    self.mas_edit.setText(f'{self.mAs:#.2f}')
    self.mas_eff_edit.setText(f'{self.eff_mAs:#.2f}')
    self.ctdiw_edit.setText(f'{self.CTDIw:#.2f}')
    self.ctdiv_c_edit.setText(f'{self.CTDIv:#.2f}')
    self.dlp_c_edit.setText(f'{self.DLP:#.2f}')
    self.disable_warning = False
