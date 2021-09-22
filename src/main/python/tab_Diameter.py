import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtSql import QSqlQueryModel, QSqlTableModel
from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                             QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QMessageBox, QProgressDialog,
                             QPushButton, QRadioButton, QScrollArea, QSpinBox,
                             QStackedWidget, QVBoxLayout, QWidget)
from scipy import interpolate

from constants import *
from image_processing import (get_center, get_center_max, get_correction_mask,
                              get_deff_correction, get_deff_value,
                              get_dw_value, get_img_no_table, get_mask,
                              get_mask_pos, windowing)
from Plot import PlotDialog


class DiameterTab(QDialog):
  def __init__(self, ctx, par, *args, **kwargs):
    super(DiameterTab, self).__init__(*args, **kwargs)
    self.baseon_items = ['Effective Diameter (Deff)', 'Water Equivalent Diameter (Dw)']
    self.src_method_items = {
      'Get from Image': ['Auto', 'Auto (Z-axis)', 'Manual'],
      'Input Manually': ['Manual'],
    }

    self.ctx = ctx
    self.par = par
    self.deff_auto_method = 'area'
    self.deff_manual_method = 'deff'
    self.d_3d_method = 'slice step'
    self.is_truncated = False
    self.is_largest_only = False
    self.is_no_roi = False
    self.is_no_table = False
    self.is_corr = [False, False]
    self.all_slices = False
    self.minimum_area = 500
    self.threshold = -300
    self.bone_limit = 250
    self.stissue_limit = -250

    self.initVar()
    self.initModel()
    self.initData()
    self.initUI()
    self.sigConnect()
    self.on_set_opts_panel()

  def initUI(self):
    self.figure = PlotDialog()
    self._menu_ui()
    self._opts_ui()
    self._set_layout()

  def initVar(self):
    self.lineAP = self.lineLAT = 0
    self.idxs = []
    self.d_vals = []
    self.show_graph = False

  def initModel(self):
    self.query_model = QSqlQueryModel()
    self.age_model = QSqlTableModel(db=self.ctx.database.deff_db)
    self.head_ap_model = QSqlTableModel(db=self.ctx.database.deff_db)
    self.head_lat_model = QSqlTableModel(db=self.ctx.database.deff_db)
    self.head_latap_model = QSqlTableModel(db=self.ctx.database.deff_db)
    self.thorax_ap_model = QSqlTableModel(db=self.ctx.database.deff_db)
    self.thorax_lat_model = QSqlTableModel(db=self.ctx.database.deff_db)
    self.thorax_latap_model = QSqlTableModel(db=self.ctx.database.deff_db)
    self.age_model.setTable("Age")
    self.head_ap_model.setTable("HeadAP")
    self.head_lat_model.setTable("HeadLAT")
    self.head_latap_model.setTable("HeadLATAP")
    self.thorax_ap_model.setTable("ThoraxAP")
    self.thorax_lat_model.setTable("ThoraxLAT")
    self.thorax_latap_model.setTable("ThoraxLATAP")

    self.age_model.select()
    self.head_ap_model.select()
    self.head_lat_model.select()
    self.head_latap_model.select()
    self.thorax_ap_model.select()
    self.thorax_lat_model.select()
    self.thorax_latap_model.select()

  def initData(self):
    self.age_data = self.getData(self.age_model)
    self.head_ap_data = self.getData(self.head_ap_model)
    self.head_lat_data = self.getData(self.head_lat_model)
    self.head_latap_data = self.getData(self.head_latap_model)
    self.thorax_ap_data = self.getData(self.thorax_ap_model)
    self.thorax_lat_data = self.getData(self.thorax_lat_model)
    self.thorax_latap_data = self.getData(self.thorax_latap_model)

    self.age_interp = interpolate.splrep(self.age_data[:,0], self.age_data[:,1])
    self.head_ap_interp = interpolate.splrep(self.head_ap_data[:,0], self.head_ap_data[:,1])
    self.head_lat_interp = interpolate.splrep(self.head_lat_data[:,0], self.head_lat_data[:,1])
    self.head_latap_interp = interpolate.splrep(self.head_latap_data[:,0], self.head_latap_data[:,1])
    self.thorax_ap_interp = interpolate.splrep(self.thorax_ap_data[:,0], self.thorax_ap_data[:,1])
    self.thorax_lat_interp = interpolate.splrep(self.thorax_lat_data[:,0], self.thorax_lat_data[:,1])
    self.thorax_latap_interp = interpolate.splrep(self.thorax_latap_data[:,0], self.thorax_latap_data[:,1])

  def _menu_ui(self):
    self.baseon_cb = QComboBox()
    self.source_cb = QComboBox()
    self.method_cb = QComboBox()
    self.calculate_btn = QPushButton('Calculate')
    self.plot_chk = QCheckBox('Show Graph')
    self.all_slices_chk = QCheckBox('All Slices')
    self.d_edit = QLineEdit(f'{self.ctx.app_data.diameter}')
    self.next_tab_btn = QPushButton('Next')
    self.prev_tab_btn = QPushButton('Previous')

    self.all_slices_chk.setVisible(False)
    self.baseon_cb.addItems(self.baseon_items)
    self.source_cb.addItems(self.src_method_items.keys())
    self.method_cb.addItems(self.src_method_items[list(self.src_method_items.keys())[0]])
    self.d_edit.setMaximumWidth(50)
    self.d_edit.setValidator(QDoubleValidator())
    self.d_edit.setReadOnly(True)

    self.calculate_btn.setAutoDefault(True)
    self.calculate_btn.setDefault(True)
    self.next_tab_btn.setAutoDefault(False)
    self.next_tab_btn.setDefault(False)
    self.prev_tab_btn.setAutoDefault(False)
    self.prev_tab_btn.setDefault(False)

    out_layout = QHBoxLayout()
    out_layout.addWidget(self.calculate_btn)
    out_layout.addWidget(QLabel('Diameter'))
    out_layout.addWidget(self.d_edit)
    out_layout.addWidget(QLabel('cm'))
    out_layout.addStretch()

    chk_layout = QHBoxLayout()
    chk_layout.addWidget(self.plot_chk)
    chk_layout.addWidget(self.all_slices_chk)
    chk_layout.addStretch()

    menu_layout = QVBoxLayout()
    menu_layout.addWidget(QLabel('Based on:'))
    menu_layout.addWidget(self.baseon_cb)
    menu_layout.addWidget(QLabel('Source:'))
    menu_layout.addWidget(self.source_cb)
    menu_layout.addWidget(QLabel('Method:'))
    menu_layout.addWidget(self.method_cb)
    menu_layout.addWidget(QLabel(''))
    menu_layout.addLayout(out_layout)
    menu_layout.addLayout(chk_layout)
    menu_layout.addStretch()

    self.menu_grpbox = QGroupBox('', self)
    self.menu_grpbox.setLayout(menu_layout)

  def _deff_correction_ui(self):
    self.bone_chk = QCheckBox("Bone")
    self.lung_chk = QCheckBox("Lung")
    self.bone_sb = QSpinBox()
    self.stissue_sb = QSpinBox()

    self.bone_sb.setRange(np.iinfo('int16').min, np.iinfo('int16').max)
    self.bone_sb.setValue(self.bone_limit)
    self.bone_sb.setMaximumWidth(60)
    self.stissue_sb.setRange(np.iinfo('int16').min, np.iinfo('int16').max)
    self.stissue_sb.setValue(self.stissue_limit)
    self.stissue_sb.setMaximumWidth(60)

    chk_layout = QHBoxLayout()
    chk_layout.addWidget(self.lung_chk)
    chk_layout.addWidget(self.bone_chk)

    corr_form = QFormLayout()
    corr_form.addRow(QLabel('Bone (HU)'), self.bone_sb)
    corr_form.addRow(QLabel('Soft Tissue (HU)'), self.stissue_sb)

    self.lower_bnd_grpbox = QGroupBox('Lower Bound')
    self.lower_bnd_grpbox.setLayout(corr_form)
    self.lower_bnd_grpbox.setEnabled(False)

    corr_layout = QVBoxLayout()
    corr_layout.addLayout(chk_layout)
    corr_layout.addWidget(self.lower_bnd_grpbox)

    self.deff_auto_corr_grpbox = QGroupBox('Correction', self)
    self.deff_auto_corr_grpbox.setLayout(corr_layout)

  def _3d_opts_ui(self):
    self.to_lbl = QLabel('to')
    self.slice1_sb = QSpinBox()
    self.slice2_sb = QSpinBox()
    self.slice_step_rbtn = QRadioButton('Slice Step')
    self.slice_nmbr_rbtn = QRadioButton('Slice Number')
    self.slice_regn_rbtn = QRadioButton('Regional')
    self.d_3d_rbtns = [self.slice_step_rbtn, self.slice_nmbr_rbtn, self.slice_regn_rbtn]

    self.d_3d_btngrp = QButtonGroup()
    [self.d_3d_btngrp.addButton(btn) for btn in self.d_3d_rbtns]

    self.slice_step_rbtn.setChecked(True)
    self.slice1_sb.setMaximum(self.ctx.total_img)
    self.slice1_sb.setMinimum(1)
    self.slice1_sb.setMinimumWidth(50)
    self.slice2_sb.setMaximum(self.ctx.total_img)
    self.slice2_sb.setMinimum(1)
    self.slice2_sb.setMinimumWidth(50)
    self.to_lbl.setHidden(True)
    self.slice2_sb.setHidden(True)

    slice_layout = QHBoxLayout()
    slice_layout.addWidget(self.slice1_sb)
    slice_layout.addWidget(self.to_lbl)
    slice_layout.addWidget(self.slice2_sb)
    slice_layout.addStretch()

    self.d_3d_grpbox = QGroupBox('Z-axis Options', self)
    d_3d_layout = QVBoxLayout()
    [d_3d_layout.addWidget(btn) for btn in self.d_3d_rbtns]
    d_3d_layout.addLayout(slice_layout)
    d_3d_layout.addStretch()
    self.d_3d_grpbox.setLayout(d_3d_layout)

  def _deff_auto_ui(self):
    self.deff_minimum_area_sb = QSpinBox()
    self.deff_threshold_sb = QSpinBox()
    self.ap_edit = QLineEdit('0 cm')
    self.lat_edit = QLineEdit('0 cm')
    self.area_rbtn = QRadioButton('Area')
    self.center_rbtn = QRadioButton('Center')
    self.max_rbtn = QRadioButton('Max')
    self.deff_auto_rbtns = [self.area_rbtn, self.center_rbtn, self.max_rbtn]

    self.deff_auto_btngrp = QButtonGroup()
    [self.deff_auto_btngrp.addButton(btn) for btn in self.deff_auto_rbtns]

    self.deff_threshold_sb.setRange(np.iinfo('int16').min, np.iinfo('int16').max)
    self.deff_threshold_sb.setValue(self.threshold)
    self.deff_threshold_sb.setMaximumWidth(60)
    self.deff_minimum_area_sb.setMaximum(512*512)
    self.deff_minimum_area_sb.setValue(self.minimum_area)
    self.deff_minimum_area_sb.setMaximumWidth(60)
    self.area_rbtn.setChecked(True)
    self.ap_edit.setMaximumWidth(60)
    self.lat_edit.setMaximumWidth(60)
    self.ap_edit.setReadOnly(True)
    self.lat_edit.setReadOnly(True)

    info_form = QFormLayout()
    info_form.addRow(QLabel('AP'), self.ap_edit)
    info_form.addRow(QLabel('LAT'), self.lat_edit)

    self.deff_auto_info_widget = QWidget()
    self.deff_auto_info_widget.setLayout(info_form)
    self.deff_auto_info_widget.setContentsMargins(0,0,0,0)

    method_layout = QVBoxLayout()
    [method_layout.addWidget(btn) for btn in self.deff_auto_rbtns]
    method_layout.addStretch()

    method_info_layout = QHBoxLayout()
    method_info_layout.addLayout(method_layout)
    method_info_layout.addWidget(self.deff_auto_info_widget)

    deff_auto_method_grpbox = QGroupBox('Method', self)
    deff_auto_method_grpbox.setLayout(method_info_layout)

    self.deff_auto_grpbox = QGroupBox('Options', self)
    deff_auto_layout = QFormLayout()
    deff_auto_layout.addRow(QLabel('Threshold (HU)'), self.deff_threshold_sb)
    deff_auto_layout.addRow(QLabel('Min. pixel area'), self.deff_minimum_area_sb)
    deff_auto_layout.addRow(deff_auto_method_grpbox)
    self.deff_auto_grpbox.setLayout(deff_auto_layout)

  def _deff_img_manual_ui(self):
    self.deff_ap_edit = QLineEdit(f'{self.lineAP:#.2f} cm') if self.lineAP else QLineEdit('0 cm')
    self.deff_lat_edit = QLineEdit(f'{self.lineLAT:#.2f} cm') if self.lineLAT else QLineEdit('0 cm')
    self.deff_ap_btn = QPushButton('AP')
    self.deff_lat_btn = QPushButton('LAT')
    self.deff_clear_btn = QPushButton('Clear')
    btns = [self.deff_ap_btn, self.deff_lat_btn, self.deff_clear_btn]

    self.deff_clear_btn.setMaximumWidth(100)
    self.deff_ap_edit.setMaximumWidth(60)
    self.deff_lat_edit.setMaximumWidth(60)
    self.deff_ap_edit.setReadOnly(True)
    self.deff_lat_edit.setReadOnly(True)
    [btn.setAutoDefault(False) for btn in btns]
    [btn.setDefault(False) for btn in btns]

    form = QFormLayout()
    form.addRow(self.deff_ap_btn, self.deff_ap_edit)
    form.addRow(self.deff_lat_btn, self.deff_lat_edit)
    form.addRow(self.deff_clear_btn)

    self.deff_img_manual_grpbox = QGroupBox('Options', self)
    self.deff_img_manual_grpbox.setLayout(form)

  def _deff_manual_ui(self):
    self.deff_man_opts_cb = QComboBox()
    self.deff_man_opts_cb.addItems(['Deff', 'AP', 'LAT', 'AP+LAT', 'AGE'])

    self.year_sb = QSpinBox()
    self.month_sb = QSpinBox()
    self.deff_man_edit1 = QLineEdit()
    self.deff_man_edit2 = QLineEdit()
    self.deff_man_unit1 = QLabel('cm')
    self.deff_man_unit2 = QLabel('cm')

    self.year_sb.setRange(0, self.age_data[-1,0])
    self.month_sb.setRange(0, 11)
    self.month_sb.setWrapping(True)

    self.deff_man_edit1.setPlaceholderText('Deff')
    self.deff_man_edit1.setValidator(QDoubleValidator())
    self.deff_man_edit2.setPlaceholderText('LAT')
    self.deff_man_edit2.setValidator(QDoubleValidator())

    self.deff_man_stack1 = QStackedWidget()
    self.deff_man_stack1.setMaximumWidth(50)
    self.deff_man_stack1.setMaximumHeight(25)
    self.deff_man_stack1.addWidget(self.deff_man_edit1)
    self.deff_man_stack1.addWidget(self.year_sb)

    self.deff_man_stack2 = QStackedWidget()
    self.deff_man_stack2.setMaximumWidth(50)
    self.deff_man_stack2.setMaximumHeight(25)
    self.deff_man_stack2.addWidget(self.deff_man_edit2)
    self.deff_man_stack2.addWidget(self.month_sb)

    h1 = QHBoxLayout()
    h1.addWidget(self.deff_man_stack1)
    h1.addWidget(self.deff_man_unit1)
    h2 = QHBoxLayout()
    h2.addWidget(self.deff_man_stack2)
    h2.addWidget(self.deff_man_unit2)

    form = QVBoxLayout()
    form.addWidget(self.deff_man_opts_cb)
    form.addLayout(h1)
    form.addLayout(h2)
    form.addStretch()

    self.deff_manual_grpbox = QGroupBox('Options')
    self.deff_manual_grpbox.setLayout(form)

    # self.deff_man_edit2.setHidden(True)
    self.deff_man_stack2.setHidden(True)
    self.deff_man_unit2.setHidden(True)

  def _dw_auto_ui(self):
    self.dw_minimum_area_lbl = QLabel('Min. pixel area')
    self.dw_threshold_lbl = QLabel('Threshold (HU)')
    self.dw_minimum_area_sb = QSpinBox()
    self.dw_threshold_sb = QSpinBox()
    self.trunc_img_chk = QCheckBox('Truncated image')
    self.large_obj_chk = QCheckBox('Largest object only')
    self.no_roi_chk = QCheckBox('Without ROI')
    self.no_table_chk = QCheckBox('Remove table')
    self.dw_auto_grpbox = QGroupBox('Options', self)
    self.no_table_chk.setEnabled(False)

    self.dw_threshold_sb.setRange(np.iinfo('int16').min, np.iinfo('int16').max)
    self.dw_threshold_sb.setValue(self.threshold)
    self.dw_threshold_sb.setMaximumWidth(60)
    self.dw_minimum_area_sb.setMaximum(512*512)
    self.dw_minimum_area_sb.setValue(self.minimum_area)
    self.dw_minimum_area_sb.setMaximumWidth(60)

    dw_auto_layout = QFormLayout()
    dw_auto_layout.addRow(self.dw_threshold_lbl, self.dw_threshold_sb)
    dw_auto_layout.addRow(self.dw_minimum_area_lbl, self.dw_minimum_area_sb)
    dw_auto_layout.addRow(self.trunc_img_chk)
    dw_auto_layout.addRow(self.large_obj_chk)
    dw_auto_layout.addRow(self.no_roi_chk)
    dw_auto_layout.addRow(self.no_table_chk)
    # dw_auto_layout.addStretch()
    self.dw_auto_grpbox.setLayout(dw_auto_layout)

  def _dw_img_manual_ui(self):
    self.dw_polygon_btn = QPushButton('Polygon')
    self.dw_ellipse_btn = QPushButton('Ellipse')
    self.dw_clear_btn = QPushButton('Clear')
    btns = [self.dw_polygon_btn, self.dw_ellipse_btn, self.dw_clear_btn]

    [btn.setMaximumWidth(100) for btn in btns]
    [btn.setAutoDefault(False) for btn in btns]
    [btn.setDefault(False) for btn in btns]

    dw_img_manual_layout = QVBoxLayout()
    [dw_img_manual_layout.addWidget(btn) for btn in btns]
    dw_img_manual_layout.addStretch()

    self.dw_img_manual_grpbox = QGroupBox('Options')
    self.dw_img_manual_grpbox.setLayout(dw_img_manual_layout)

  def _opts_ui(self):
    self._3d_opts_ui()
    self._deff_auto_ui()
    self._deff_img_manual_ui()
    self._deff_manual_ui()
    self._dw_auto_ui()
    self._dw_img_manual_ui()
    self._deff_correction_ui()

    self.opts_stack = QStackedWidget()
    self.opts_stack.addWidget(self.deff_auto_grpbox)
    self.opts_stack.addWidget(self.deff_img_manual_grpbox)
    self.opts_stack.addWidget(self.deff_manual_grpbox)
    self.opts_stack.addWidget(self.dw_auto_grpbox)
    self.opts_stack.addWidget(self.dw_img_manual_grpbox)

    opts_layout = QVBoxLayout()
    opts_layout.addWidget(self.opts_stack)
    opts_layout.addWidget(self.deff_auto_corr_grpbox)
    opts_layout.addWidget(self.d_3d_grpbox)
    opts_layout.addStretch()

    opts_widget = QWidget()
    opts_widget.setContentsMargins(0,0,0,0)
    opts_widget.setLayout(opts_layout)

    self.opts_scroll = QScrollArea()
    self.opts_scroll.setWidget(opts_widget)
    self.opts_scroll.setWidgetResizable(True)
    self.opts_scroll.horizontalScrollBar().setEnabled(False);

    self.d_3d_grpbox.setVisible(False)

  def _set_layout(self):
    menu_layout = QHBoxLayout()
    menu_layout.addWidget(self.menu_grpbox)
    menu_layout.addWidget(self.opts_scroll)

    tab_nav = QHBoxLayout()
    tab_nav.addWidget(self.prev_tab_btn)
    tab_nav.addStretch()
    tab_nav.addWidget(self.next_tab_btn)

    main_layout = QVBoxLayout()
    main_layout.addLayout(menu_layout)
    main_layout.addLayout(tab_nav)
    self.setLayout(main_layout)

  def sigConnect(self):
    self.baseon_cb.activated[str].connect(self.on_set_opts_panel)
    self.method_cb.activated[str].connect(self.on_set_opts_panel)
    self.source_cb.activated[str].connect(self.on_set_opts_panel)
    self.source_cb.activated[str].connect(self.on_source_changed)
    self.deff_man_opts_cb.activated[str].connect(self.on_deff_manual_method_changed)
    self.year_sb.valueChanged.connect(self.check_age)
    self.trunc_img_chk.stateChanged.connect(self.on_truncated_check)
    self.large_obj_chk.stateChanged.connect(self.on_largest_check)
    self.no_roi_chk.stateChanged.connect(self.on_roi_check)
    self.no_table_chk.stateChanged.connect(self.on_table_check)
    self.calculate_btn.clicked.connect(self.on_calculate)
    self.deff_clear_btn.clicked.connect(self.clearROIs)
    self.dw_clear_btn.clicked.connect(self.clearROIs)
    self.deff_minimum_area_sb.valueChanged.connect(self.on_minimum_area_changed)
    self.dw_minimum_area_sb.valueChanged.connect(self.on_minimum_area_changed)
    self.deff_threshold_sb.valueChanged.connect(self.on_threshold_changed)
    self.dw_threshold_sb.valueChanged.connect(self.on_threshold_changed)
    self.dw_ellipse_btn.clicked.connect(self.add_ellipse)
    self.dw_polygon_btn.clicked.connect(self.add_polygon)
    self.deff_ap_btn.clicked.connect(self.add_ap_line)
    self.deff_lat_btn.clicked.connect(self.add_lat_line)
    self.bone_chk.stateChanged.connect(self.on_corr_check)
    self.lung_chk.stateChanged.connect(self.on_corr_check)
    self.bone_sb.valueChanged.connect(self.on_bone_limit_changed)
    self.stissue_sb.valueChanged.connect(self.on_stissue_limit_changed)
    self.ctx.app_data.imgLoaded.connect(self.img_loaded_handle)
    self.ctx.app_data.imgChanged.connect(self.img_changed_handle)
    self.ctx.app_data.sliceOptChanged.connect(self.sliceopt_handle)
    self.ctx.app_data.mode3dChanged.connect(self.mode3d_handle)
    self.ctx.app_data.slice1Changed.connect(self.slice1_handle)
    self.ctx.app_data.slice2Changed.connect(self.slice2_handle)
    [btn.toggled.connect(self.on_deff_auto_method_changed) for btn in self.deff_auto_rbtns]
    [btn.toggled.connect(self.on_3d_opts_changed) for btn in self.d_3d_rbtns]
    self.plot_chk.stateChanged.connect(self.on_show_graph_check)
    self.all_slices_chk.stateChanged.connect(self.on_all_slices)

  def on_all_slices(self, state):
    self.all_slices = state == Qt.Checked
    self.ctx.app_data.d_mode = int(self.all_slices)

  def img_loaded_handle(self, state):
    if not state:
      self.all_slices = False
      self.all_slices_chk.setChecked(False)
    self.all_slices_chk.setEnabled(state)

  def on_show_graph_check(self, state):
    self.show_graph = state == Qt.Checked

  def plot_chk_handle(self, state):
    self.plot_chk.setEnabled(state)
    self.show_graph = False
    self.plot_chk.setCheckState(Qt.Unchecked)

  def getData(self, model):
    data = [[model.data(model.index(i,j)) for i in range(model.rowCount())] for j in range(1,3)]
    return np.array(data).T

  def check_age(self, val):
    if val==self.age_data[-1,0]:
      self.month_sb.setMaximum(0)
    else:
      self.month_sb.setMaximum(11)

  def on_truncated_check(self, state):
    self.is_truncated = state == Qt.Checked

  def on_largest_check(self, state):
    self.is_largest_only = state == Qt.Checked

  def on_roi_check(self, state):
    self.is_no_roi = state == Qt.Checked
    if self.is_no_roi:
      self.large_obj_chk.setCheckState(Qt.Unchecked)
      self.trunc_img_chk.setCheckState(Qt.Unchecked)
      self.is_largest_only = False
      self.is_truncated = False
    else:
      self.no_table_chk.setCheckState(Qt.Unchecked)
      self.is_no_table = False
    self.no_table_chk.setEnabled(self.is_no_roi)
    self.large_obj_chk.setEnabled(not self.is_no_roi)
    self.trunc_img_chk.setEnabled(not self.is_no_roi)
    self.dw_minimum_area_lbl.setEnabled(not self.is_no_roi)
    self.dw_minimum_area_sb.setEnabled(not self.is_no_roi)
    self.dw_threshold_lbl.setEnabled(not self.is_no_roi)
    self.dw_threshold_sb.setEnabled(not self.is_no_roi)

  def on_table_check(self, state):
    self.is_no_table = state == Qt.Checked
    self.dw_threshold_lbl.setEnabled(self.is_no_table)
    self.dw_threshold_sb.setEnabled(self.is_no_table)

  def on_corr_check(self, state):
    self.is_corr[int(self.sender().text().lower() == 'bone')] = state == Qt.Checked
    self.lower_bnd_grpbox.setEnabled(any(self.is_corr))

  def on_source_changed(self, src):
    self.method_cb.clear()
    self.method_cb.addItems(self.src_method_items[src])
    self.on_set_opts_panel()

  def on_deff_auto_method_changed(self):
    self.clearROIs()
    sel = self.sender()
    if sel.isChecked():
      self.deff_auto_method = sel.text().lower()
      is_area = self.deff_auto_method == 'area'
      self.deff_auto_corr_grpbox.setVisible(not is_area)
      if self.method == 0: self.deff_auto_info_widget.setVisible(not is_area)
      if is_area:
        self.bone_chk.setCheckState(Qt.Unchecked)
        self.lung_chk.setCheckState(Qt.Unchecked)
        self.is_corr = [False, False]
      print(self.deff_auto_method)

  def on_3d_opts_changed(self):
    sel = self.sender()
    if sel.isChecked():
      self.d_3d_method = sel.text().lower()
      if self.d_3d_method == 'regional':
        self.to_lbl.setHidden(False)
        self.slice2_sb.setHidden(False)
        self.slice1_sb.setMinimum(1)
        self.slice1_sb.setMaximum(self.ctx.total_img)
      else:
        self.to_lbl.setHidden(True)
        self.slice2_sb.setHidden(True)

  def on_set_opts_panel(self):
    self.clearROIs()
    self.opts_stack.setVisible(True)
    self.deff_auto_info_widget.setVisible(False)
    self.d_3d_grpbox.setVisible(False)
    self.deff_auto_corr_grpbox.setVisible(False)
    self.d_edit.setReadOnly(True)
    self.baseon = self.baseon_cb.currentIndex()
    self.source = self.source_cb.currentIndex()
    self.method = self.method_cb.currentIndex()
    try:
      self.d_edit.textChanged.disconnect(self._on_dw_manual)
    except:
      pass
    self.all_slices_chk.setVisible(self.source==1)
    if self.source == 1:# and (self.sender().tag is 'source' or self.sender().tag is 'based'):
      if self.baseon == 0 and self.method == 0:
        self.plot_chk_handle(True)
        self.opts_stack.setCurrentIndex(2)
        self.ctx.app_data.mode = DEFF_MANUAL
      else:
        self.opts_stack.setVisible(False)
        self.ctx.app_data.mode = DW
        self.d_edit.setReadOnly(False)
        self.d_edit.textChanged.connect(self._on_dw_manual)
    elif self.source == 0: # from img
      self.d_3d_grpbox.setVisible(self.method == 1)
      self.plot_chk_handle(self.method == 1)
      if self.baseon == 0: # deff
        if self.method == 0 or self.method == 1:
          self.deff_auto_corr_grpbox.setVisible(self.deff_auto_method != 'area')
          self.opts_stack.setCurrentIndex(0)
          if self.method == 0:
            self.deff_auto_info_widget.setVisible(self.deff_auto_method != 'area')
        elif self.method == 2:
          self.opts_stack.setCurrentIndex(1)
        self.ctx.app_data.mode = DEFF_IMAGE
      else:
        if self.method == 0 or self.method == 1:
          self.opts_stack.setCurrentIndex(3)
        elif self.method == 2:
          self.opts_stack.setCurrentIndex(4)
        self.ctx.app_data.mode = DW
    self.d_edit.setText('0')

  def on_deff_manual_method_changed(self, sel):
    self.deff_man_edit1.clear()
    self.deff_man_edit2.clear()
    if sel.lower() != 'ap+lat' and sel.lower() != 'age':
      self.deff_man_stack1.setCurrentIndex(0)
      self.deff_man_stack2.setCurrentIndex(0)
      self.deff_man_edit1.setPlaceholderText(sel)
      self.deff_man_unit1.setText('cm')
      self.deff_man_stack2.setHidden(True)
      self.deff_man_unit2.setHidden(True)
      if sel.lower() == 'deff':
        self.ctx.app_data.mode = DEFF_MANUAL
      else:
        self.ctx.app_data.mode = DEFF_AP if sel.lower()=='ap' else DEFF_LAT
    else:
      self.deff_man_stack2.setHidden(False)
      self.deff_man_unit2.setHidden(False)
      if sel.lower() == 'age':
        self.deff_man_stack1.setCurrentIndex(1)
        self.deff_man_stack2.setCurrentIndex(1)
        self.deff_man_unit1.setText('year(s)')
        self.deff_man_unit2.setText('month(s)')
        self.ctx.app_data.mode = DEFF_AGE
      else:
        self.deff_man_stack1.setCurrentIndex(0)
        self.deff_man_stack2.setCurrentIndex(0)
        self.deff_man_edit1.setPlaceholderText('AP')
        self.deff_man_edit2.setPlaceholderText('LAT')
        self.deff_man_unit1.setText('cm')
        self.deff_man_unit2.setText('cm')
        self.ctx.app_data.mode = DEFF_APLAT
      self.d_edit.setReadOnly(True)
    self.deff_manual_method = sel.lower()
    print(self.deff_manual_method)
    self.d_edit.setText('0')

  def _on_dw_manual(self, text):
    try:
      self.ctx.app_data.diameter = float(text)
    except:
      self.ctx.app_data.diameter = 0

  def on_minimum_area_changed(self):
    sender = self.sender()
    self.minimum_area = sender.value()
    if sender == self.deff_minimum_area_sb:
      self.dw_minimum_area_sb.setValue(self.minimum_area)
    else:
      self.deff_minimum_area_sb.setValue(self.minimum_area)

  def on_threshold_changed(self):
    sender = self.sender()
    self.threshold = sender.value()
    if sender == self.deff_threshold_sb:
      self.dw_threshold_sb.setValue(self.threshold)
    else:
      self.deff_threshold_sb.setValue(self.threshold)

  def on_bone_limit_changed(self):
    self.bone_limit = self.bone_sb.value()

  def on_stissue_limit_changed(self):
    self.stissue_limit = self.stissue_sb.value()

  def on_calculate(self):
    self.ctx.app_data.d_mode = 0
    if self.source == 0: # from img
      if not self.ctx.isImage:
        QMessageBox.warning(None, "Warning", "Open DICOM files first.")
        return
      if self.method == 0: # auto
        self.calculate_auto()
      elif self.method == 1: # 3d
        self.ctx.app_data.d_mode = 1
        self.calculate_auto_3d()
      elif self.method == 2: # manual
        self.calculate_img_manual()
    elif self.source == 1: # input manual
      self.calculate_manual()
    self.next_tab_btn.setAutoDefault(True)
    self.next_tab_btn.setDefault(True)
    self.calculate_btn.setAutoDefault(False)
    self.calculate_btn.setDefault(False)

  def calculate_auto(self):
    self.ctx.axes.clearGraph()
    img = self.ctx.get_current_img()
    dims = self.ctx.img_dims
    rd = self.ctx.recons_dim
    img_to_show = img.copy()
    dval = 0
    mask = None
    correction = 0

    if self.baseon == 0: # deff
      mask = self.get_img_mask(img, threshold=self.threshold, minimum_area=self.minimum_area, largest_only=True)
      if mask is None:
        return
      correction = sum(v<<i for i, v in enumerate(self.is_corr[::-1]))
      if correction and self.deff_auto_method!='area':
        center = get_center(mask) if self.deff_auto_method == 'center' else get_center_max(mask)
        corr_mask = get_correction_mask(img, mask, lb_bone=self.bone_limit, lb_stissue=self.stissue_limit)
        dval, ap, lat = get_deff_correction(self.is_corr, corr_mask, center, rd)
        row, col = center
        img_to_show = corr_mask
      else:
        dval, row, col, ap, lat = get_deff_value(mask, dims, rd, self.deff_auto_method)
      if self.deff_auto_method != 'area':
        self.plot_ap_lat(mask, row, col)
        self.ap_edit.setText(f'{ap:#.2f} cm')
        self.lat_edit.setText(f'{lat:#.2f} cm')

    elif self.baseon == 1:
      if self.is_no_roi:
        mask = np.ones_like(img,  dtype=bool)
        if self.is_no_table:
          img_to_show = get_img_no_table(img, threshold=self.threshold)
          img = img_to_show.copy()
        img[img<-1000] = -1000
      else:
        mask = self.get_img_mask(img, threshold=self.threshold, minimum_area=self.minimum_area, largest_only=self.is_largest_only)
        if mask is None:
          return
      dval = get_dw_value(img, mask, dims, rd, self.is_truncated, self.is_largest_only)

    self.d_edit.setText(f'{dval:#.2f}')
    self.ctx.app_data.diameter = dval
    self.ctx.app_data.diameters[self.ctx.current_img] = dval
    self.ctx.app_data.emit_d_changed()

    if isinstance(self.par.window_width, int) and isinstance(self.par.window_level, int) and correction==0:
      img_to_show = windowing(img_to_show, self.par.window_width, self.par.window_level)
    self.ctx.axes.add_alt_view(img_to_show)
    self.plot_mask(mask)

  def calculate_auto_3d(self):
    self.d_vals = []
    self.idxs = []
    nslice = self.slice1_sb.value()
    dcms = np.array(self.ctx.dicoms)
    index = list(range(len(dcms)))

    if self.d_3d_method  == 'slice step':
      idxs = index[::nslice]
      imgs = dcms[::nslice]
    elif self.d_3d_method  == 'slice number':
      tmps = np.array_split(np.arange(len(dcms)), nslice)
      idxs = [tmp[len(tmp)//2] for tmp in tmps]
      imgs = dcms[idxs]
    elif self.d_3d_method  == 'regional':
      nslice2 = self.slice2_sb.value()
      first = nslice if nslice<=nslice2 else nslice2
      last = nslice2 if nslice<=nslice2 else nslice
      idxs = index[first-1:last]
      imgs = dcms[first-1:last]
    else:
      imgs = dcms
      idxs = index

    avg_dval, idxs = self.get_avg_diameter(imgs, idxs)
    self.d_edit.setText(f'{avg_dval:#.2f}')
    self.ctx.app_data.diameter = avg_dval
    self.idxs = [i+1 for i in idxs]
    for k, v in zip(self.idxs, self.d_vals):
      self.ctx.app_data.diameters[k] = v
    self.ctx.app_data.emit_d_changed()
    if self.show_graph:
      self.plot_3d_auto()

  def calculate_img_manual(self):
    pass

  def calculate_manual(self):
    if self.baseon == 0: # deff
      if self.deff_manual_method == 'deff':
        label = 'Effective Diameter'
        unit = 'cm'
        try:
          dval = float(self.deff_man_edit1.text())
        except:
          dval = 0
        val1 = dval
        data = np.array([np.arange(0,2*val1,.01) for _ in range(2)]).T
      elif self.deff_manual_method == 'age':
        label = 'Age'
        unit = 'year'
        year = self.year_sb.value()
        month = self.month_sb.value()
        val1 = year + month/12
        data = self.age_data
        dval = float(interpolate.splev(val1, self.age_interp))
      else:
        unit = 'cm'
        try:
          val1 = float(self.deff_man_edit1.text())
        except:
          val1 = 0
        try:
          val2 = float(self.deff_man_edit2.text())
        except:
          val2 = 0
        if self.deff_manual_method == 'ap+lat':
          label = 'AP+LAT'
          val1 += val2
          if self.ctx.phantom == HEAD:
            interp = self.head_latap_interp
            data = self.head_latap_data
          else:
            interp = self.thorax_latap_interp
            data = self.thorax_latap_data
        elif self.deff_manual_method == 'ap':
          label = 'AP'
          if self.ctx.phantom == HEAD:
            interp = self.head_ap_interp
            data = self.head_ap_data
          else:
            interp = self.thorax_ap_interp
            data = self.thorax_ap_data
        elif self.deff_manual_method == 'lat':
          label = 'LAT'
          if self.ctx.phantom == HEAD:
            interp = self.head_lat_interp
            data = self.head_lat_data
          else:
            interp = self.thorax_lat_interp
            data = self.thorax_lat_data
        if val1 < data[0,0] or val1 > data[-1,0]:
          QMessageBox.information(None, "Information",
            f"The result is an extrapolated value.\nFor the best result, input value between {data[0,0]} and {data[-1,0]}.")
        dval = float(interpolate.splev(val1, interp))

      if self.show_graph:
        self.figure = PlotDialog()
        self.figure.actionEnabled(True)
        self.figure.trendActionEnabled(False)
        self.figure.plot(data, pen={'color': "FFFF00", 'width': 2}, symbol=None)
        self.figure.plot([val1], [dval], symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
        self.figure.annotate('deff', pos=(val1,dval), text=f'{label}: {val1:#.2f} {unit}\nEffective Diameter: {dval:#.2f} cm')
        self.figure.axes.showGrid(True,True)
        self.figure.setLabels(label,'Effective Diameter',unit,'cm')
        self.figure.setTitle(f'{label} - Deff')
        self.figure.show()
    else:
      dval = float(self.d_edit.text())
    self.d_edit.setText(f'{dval:#.2f}')
    self.ctx.app_data.diameter = dval
    if self.all_slices:
      self.idxs = list(range(1, self.ctx.total_img+1))
      for idx in self.idxs:
        self.ctx.app_data.diameters[idx] = dval
    else:
      self.ctx.app_data.diameters[self.ctx.current_img] = dval
    self.ctx.app_data.emit_d_changed()

  def clearROIs(self):
    if len(self.ctx.axes.rois) == 0:
      return
    print(self.ctx.axes.rois)
    self.ctx.axes.clearROIs()
    self.deff_ap_edit.setText('0 cm')
    self.deff_lat_edit.setText('0 cm')
    self.ap_edit.setText('0 cm')
    self.lat_edit.setText('0 cm')
    self.d_edit.setText('0')
    self.lineLAT = self.lineAP = 0
    self.ctx.app_data.diameter = 0

  def get_avg_diameter(self, dss, idxs):
    dval = 0
    n = len(dss)
    n_seg = 0
    progress = QProgressDialog(f"Calculating diameter of {n} images...", "Stop", 0, n, self)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(1000)
    for idx, dcm in enumerate(dss):
      img = self.ctx.get_img_from_ds(dcm)
      if self.baseon == 0:
        mask = get_mask(img, threshold=self.threshold, minimum_area=self.minimum_area, largest_only=True)
        if mask is not None:
          n_seg += 1
          correction = sum(v<<i for i, v in enumerate(self.is_corr[::-1]))
          if correction and self.deff_auto_method!='area':
            center = get_center(mask) if self.deff_auto_method == 'center' else get_center_max(mask)
            corr_mask = get_correction_mask(img, mask, lb_bone=self.bone_limit, lb_stissue=self.stissue_limit)
            res = get_deff_correction(self.is_corr, corr_mask, center, self.ctx.recons_dim)
          else:
            res = get_deff_value(mask, self.ctx.img_dims, self.ctx.recons_dim, self.deff_auto_method)
          d = res[0]
        else:
          d = 0
      else:
        if self.is_no_roi:
          mask = np.ones_like(img,  dtype=bool)
          if self.is_no_table:
            img = get_img_no_table(img, threshold=self.threshold)
          img[img<-1000] = -1000
        else:
          mask = get_mask(img, threshold=self.threshold, minimum_area=self.minimum_area, largest_only=self.is_largest_only)
        if mask is not None:
          n_seg += 1
          d = get_dw_value(img, mask, self.ctx.img_dims, self.ctx.recons_dim, self.is_truncated, self.is_largest_only)
        else:
          d = 0
      dval += d
      self.d_vals.append(d)
      progress.setValue(idx)
      if progress.wasCanceled():
        idxs = idxs[:idx+1]
        break
    progress.setValue(n)
    return dval/n_seg, idxs

  def get_img_mask(self, *args, **kwargs):
    mask = get_mask(*args, **kwargs)
    if mask is None:
      QMessageBox.warning(None, 'Segmentation Failed', 'No object found during segmentation process.')
    return mask

  def plot_mask(self, mask):
    pos = get_mask_pos(mask)+.5
    pos_col = pos[:,1]
    pos_row = pos[:,0]
    self.ctx.axes.immarker(pos_col, pos_row, pen=None, symbol='s', symbolPen=None, symbolSize=3, symbolBrush=(255, 0, 0, 255))

  def plot_ap_lat(self, mask, row, col):
    pos = get_mask_pos(mask)+.5
    pos_col = pos[:,1]
    pos_row = pos[:,0]
    col += .5
    row += .5
    id_row = [id for id, el in enumerate(pos_col) if el==col]
    id_col = [id for id, el in enumerate(pos_row) if el==row]
    line_v = np.array([pos_col[id_row], pos_row[id_row]]).T
    line_h = np.array([pos_col[id_col], pos_row[id_col]]).T
    self.ctx.axes.plot(line_v, pen={'color': "00FF7F", 'width': 2}, symbol=None)
    self.ctx.axes.plot(line_h, pen={'color': "00FF7F", 'width': 2}, symbol=None)
    self.ctx.axes.plot([col], [row], pen=None, symbol='o', symbolPen=None, symbolSize=10, symbolBrush=(255, 127, 0, 255))

  def plot_3d_auto(self):
    xlabel = 'Dw' if self.baseon else 'Deff'
    title = 'Water Equivalent Diameter' if self.baseon else 'Effective Diameter'
    self.figure = PlotDialog()
    self.figure.actionEnabled(True)
    self.figure.trendActionEnabled(False)
    self.figure.axes.scatterPlot.clear()
    self.figure.plot(self.idxs, self.d_vals, pen={'color': "FFFF00", 'width': 2}, symbol='o', symbolPen=None, symbolSize=8, symbolBrush=(255, 0, 0, 255))
    self.figure.axes.showGrid(True,True)
    self.figure.setLabels('slice',xlabel,'','cm')
    self.figure.setTitle(f'Slice - {title}')
    self.figure.show()

  def get_distance(self, p1, p2):
    try:
      col,row = self.ctx.get_current_img().shape
    except:
      return
    rd = self.ctx.recons_dim
    return np.sqrt(((np.array(p2)-np.array(p1))**2).sum()) * (0.1*(rd/row))

  def _roi_handle_to_tuple(self, handle):
    return (handle.pos().x(), handle.pos().y())

  def add_lat_line(self):
    if not self.ctx.isImage:
      QMessageBox.warning(None, "Warning", "Open DICOM files first.")
      return
    x, y = self.ctx.get_current_img().shape
    self.ctx.axes.addLAT(((x/2)-0.25*x, y/2), ((x/2)+0.25*x, y/2))
    self.ctx.axes.lineLAT.sigRegionChanged.connect(self.get_lat_from_line)
    pts = self.ctx.axes.lineLAT.getHandles()
    p1 = self._roi_handle_to_tuple(pts[0])
    p2 = self._roi_handle_to_tuple(pts[1])
    self.lineLAT = self.get_distance(p1, p2)
    self.deff_lat_edit.setText(f'{self.lineLAT:#.2f} cm')
    self.get_deff_from_line()

  def add_ap_line(self):
    if not self.ctx.isImage:
      QMessageBox.warning(None, "Warning", "Open DICOM files first.")
      return
    x, y = self.ctx.get_current_img().shape
    self.ctx.axes.addAP(((x/2), (y/2)-0.25*y), ((x/2), (y/2)+0.25*y))
    self.ctx.axes.lineAP.sigRegionChanged.connect(self.get_ap_from_line)
    pts = self.ctx.axes.lineAP.getHandles()
    p1 = self._roi_handle_to_tuple(pts[0])
    p2 = self._roi_handle_to_tuple(pts[1])
    self.lineAP = self.get_distance(p1, p2)
    self.deff_ap_edit.setText(f'{self.lineAP:#.2f} cm')
    self.get_deff_from_line()

  def add_ellipse(self):
    if not self.ctx.isImage:
      QMessageBox.warning(None, "Warning", "Open DICOM files first.")
      return
    self.ctx.axes.addEllipse()
    self.ctx.axes.ellipse.sigRegionChangeFinished.connect(self.get_dw_from_ellipse)
    self.get_dw_from_ellipse(self.ctx.axes.ellipse)

  def add_polygon(self):
    if not self.ctx.isImage:
      QMessageBox.warning(None, "Warning", "Open DICOM files first.")
      return
    self.ctx.axes.addPolyFinished.connect(self.get_dw_from_ellipse)
    self.ctx.axes.addPoly()
    self.ctx.axes.poly.sigRegionChangeFinished.connect(self.get_dw_from_ellipse)

  def get_lat_from_line(self, roi):
    pts = roi.getHandles()
    p1 = self._roi_handle_to_tuple(pts[0])
    p2 = self._roi_handle_to_tuple(pts[1])
    self.lineLAT = self.get_distance(p1, p2)
    self.deff_lat_edit.setText(f'{self.lineLAT:#.2f} cm')
    self.get_deff_from_line()

  def get_ap_from_line(self, roi):
    pts = roi.getHandles()
    p1 = self._roi_handle_to_tuple(pts[0])
    p2 = self._roi_handle_to_tuple(pts[1])
    self.lineAP = self.get_distance(p1, p2)
    self.deff_ap_edit.setText(f'{self.lineAP:#.2f} cm')
    self.get_deff_from_line()

  def get_deff_from_line(self):
    dval = np.sqrt(self.lineAP * self.lineLAT)
    self.d_edit.setText(f'{dval:#.2f}')
    self.ctx.app_data.diameter = dval
    self.ctx.app_data.diameters[self.ctx.current_img] = dval
    self.ctx.app_data.emit_d_changed()

  def get_dw_from_ellipse(self, roi):
    dims = self.ctx.img_dims
    rd = self.ctx.recons_dim
    img = roi.getArrayRegion(self.ctx.get_current_img(), self.ctx.axes.image, returnMappedCoords=False)
    if img.size == 0:
      return
    mask = roi.renderShapeMask(img.shape[0],img.shape[1])
    if not mask.any():
      return
    dval = get_dw_value(img, mask, dims, rd)
    self.d_edit.setText(f'{dval:#.2f}')
    self.ctx.app_data.diameter = dval
    self.ctx.app_data.diameters[self.ctx.current_img] = dval
    self.ctx.app_data.emit_d_changed()

  def img_changed_handle(self, value):
    if value:
      self.reset_fields()

  def sliceopt_handle(self, value):
    self.source_cb.setCurrentIndex(0)
    src = self.source_cb.currentText()
    self.on_source_changed(src)
    self.method_cb.setCurrentIndex(value)
    self.on_set_opts_panel()

  def mode3d_handle(self, value):
    rb = [r for r in self.d_3d_rbtns if r.text().lower()==value]
    rb[0].setChecked(True)

  def slice1_handle(self, value):
    self.slice1_sb.setValue(value)

  def slice2_handle(self, value):
    self.slice2_sb.setValue(value)

  def reset_fields(self):
    self.initVar()
    self.ctx.app_data.diameter = 0
    self.d_edit.setText('0')
    self.ap_edit.setText('0 cm')
    self.lat_edit.setText('0 cm')
    self.deff_ap_edit.setText('0 cm')
    self.deff_lat_edit.setText('0 cm')
    self.deff_man_edit1.clear()
    self.deff_man_edit2.clear()
    self.calculate_btn.setAutoDefault(True)
    self.calculate_btn.setDefault(True)
    self.next_tab_btn.setAutoDefault(False)
    self.next_tab_btn.setDefault(False)
    self.plot_chk.setCheckState(Qt.Unchecked)
