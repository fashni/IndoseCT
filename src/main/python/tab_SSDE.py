import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlTableModel
from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                             QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QRadioButton, QScrollArea, QVBoxLayout)

from constants import *
from custom_widgets import HSeparator
from db import get_records
from Plot import PlotDialog


class SSDETab(QDialog):
  def __init__(self, ctx, *args, **kwargs):
    super(SSDETab, self).__init__(*args, **kwargs)
    self.ctx = ctx
    self.show_graph = False
    self.initModel()
    self.initUI()
    self.sigConnect()

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
    self.figure = PlotDialog()
    self.protocol_cb = QComboBox()
    self.protocol_cb.setModel(self.protocol_model)
    self.protocol_cb.setModelColumn(self.protocol_model.fieldIndex('name'))
    self.report_cb = QComboBox()
    self.report_cb.setModel(self.report_model)
    self.report_cb.setModelColumn(self.report_model.fieldIndex('name'))
    self.plot_chk = QCheckBox('Show Graph')

    self.calc_btn = QPushButton('Calculate')
    self.save_btn = QPushButton('Save')

    self.calc_btn.setAutoDefault(True)
    self.calc_btn.setDefault(True)
    self.save_btn.setAutoDefault(False)
    self.save_btn.setDefault(False)

    self.diameter_label = QLabel('<b>Diameter (cm)</b>')
    self.ctdiv_edit = QLineEdit(f'{self.ctx.app_data.CTDIv}')
    self.diameter_edit = QLineEdit(f'{self.ctx.app_data.diameter}')
    self.convf_edit = QLineEdit(f'{self.ctx.app_data.convf}')
    self.ssde_edit = QLineEdit(f'{self.ctx.app_data.SSDE}')
    self.dlp_edit = QLineEdit(f'{self.ctx.app_data.DLP}')
    self.dlpc_edit = QLineEdit(f'{self.ctx.app_data.DLPc}')
    self.effdose_edit = QLineEdit(f'{self.ctx.app_data.effdose}')

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

    left_grpbox = QGroupBox()
    left_layout = QFormLayout()
    left_layout.addRow(QLabel('<b>CTDI<sub>vol</sub> (mGy)</b>'), self.ctdiv_edit)
    left_layout.addRow(self.diameter_label, self.diameter_edit)
    left_layout.addRow(QLabel('<b>Conv Factor</b>'), self.convf_edit)
    left_layout.addRow(QLabel('<b>SSDE (mGy)</b>'), self.ssde_edit)
    left_grpbox.setLayout(left_layout)

    right_grpbox = QGroupBox()
    right_layout = QFormLayout()
    right_layout.addRow(QLabel('<b>DLP (mGy-cm)</b>'), self.dlp_edit)
    right_layout.addRow(QLabel('<b>DLP<sub>c</sub> (mGy-cm)</b>'), self.dlpc_edit)
    right_layout.addRow(QLabel(''))
    right_layout.addRow(QLabel('<b>Effective Dose (mSv)</b>'), self.effdose_edit)
    right_grpbox.setLayout(right_layout)

    h = QHBoxLayout()
    h.addWidget(left_grpbox)
    h.addWidget(right_grpbox)

    tab_nav = QHBoxLayout()
    tab_nav.addWidget(self.prev_tab_btn)
    tab_nav.addStretch()
    tab_nav.addWidget(self.next_tab_btn)

    btn_layout = QHBoxLayout()
    btn_layout.addWidget(self.calc_btn)
    btn_layout.addWidget(self.save_btn)
    btn_layout.addStretch()

    main_layout = QVBoxLayout()
    main_layout.addWidget(QLabel('Based on:'))
    main_layout.addWidget(self.report_cb)
    main_layout.addWidget(QLabel('Protocol:'))
    main_layout.addWidget(self.protocol_cb)
    main_layout.addWidget(HSeparator())
    main_layout.addLayout(h)
    main_layout.addLayout(btn_layout)
    main_layout.addWidget(self.plot_chk)
    main_layout.addStretch()
    main_layout.addLayout(tab_nav)

    self.setLayout(main_layout)

  def sigConnect(self):
    self.protocol_cb.activated[int].connect(self.on_protocol_changed)
    self.report_cb.activated[int].connect(self.on_report_changed)
    self.calc_btn.clicked.connect(self.on_calculate)
    self.ctx.app_data.modeValueChanged.connect(self.diameter_mode_handle)
    self.ctx.app_data.diameterValueChanged.connect(self.diameter_handle)
    self.ctx.app_data.CTDIValueChanged.connect(self.ctdiv_handle)
    self.ctx.app_data.DLPValueChanged.connect(self.dlp_handle)
    self.ctx.app_data.imgChanged.connect(self.img_changed_handle)
    self.plot_chk.stateChanged.connect(self.on_show_graph_check)

  def plot(self, data):
    x = self.ctx.app_data.diameter
    y = self.ctx.app_data.convf
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
    if value == DW:
      self.diameter_label.setText('<b>Dw (cm)</b>')
    else:
      self.diameter_label.setText('<b>Deff (cm)</b>')

  def diameter_handle(self, value):
    self.diameter_edit.setText(f'{value:#.4f}')

  def ctdiv_handle(self, value):
    self.ctdiv_edit.setText(f'{value:#.4f}')

  def dlp_handle(self, value):
    self.dlp_edit.setText(f'{value:#.4f}')

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

  def on_calculate(self):
    minv = 6 if self.ctx.phantom == HEAD else 8
    maxv = 55 if self.ctx.phantom == HEAD else 45

    try:
      self.ctx.app_data.convf = self.cf_eq(self.ctx.app_data.diameter)
      self.ctx.app_data.SSDE = self.ctx.app_data.convf * self.ctx.app_data.CTDIv
      self.ctx.app_data.DLPc = self.ctx.app_data.convf * self.ctx.app_data.DLP
      self.ctx.app_data.effdose = self.ctx.app_data.DLP * np.exp(self.alfa*self.ctx.app_data.diameter + self.beta)
    except:
      QMessageBox.warning(None, "No Data", f"There are no data in {self.report_cb.currentText()} report for {self.ctx.phantom_name} phantom.")
      return

    deff = np.arange(minv, maxv+1, 1)
    cf = self.cf_eq(deff)
    self.data = np.array([deff, cf]).T

    self.convf_edit.setText(f'{self.ctx.app_data.convf:#.4f}')
    self.ssde_edit.setText(f'{self.ctx.app_data.SSDE:#.4f}')
    self.dlpc_edit.setText(f'{self.ctx.app_data.DLPc:#.4f}')
    self.effdose_edit.setText(f'{self.ctx.app_data.effdose:#.4f}')
    if self.show_graph:
      self.on_plot()
    self.switch_button_default(mode=1)

  def on_plot(self):
    self.plot(self.data)

  def img_changed_handle(self, value):
    if value:
      self.reset_fields()

  def reset_fields(self):
    self.ctx.app_data.convf = 0
    self.ctx.app_data.SSDE = 0
    self.ctx.app_data.DLPc = 0
    self.ctx.app_data.effdose = 0
    self.show_graph = False
    self.plot_chk.setCheckState(Qt.Unchecked)
    self.switch_button_default()
    self.ctdiv_edit.setText(f'{self.ctx.app_data.CTDIv:#.4f}')
    self.diameter_edit.setText(f'{self.ctx.app_data.diameter:#.4f}')
    self.dlp_edit.setText(f'{self.ctx.app_data.DLP:#.4f}')
    self.convf_edit.setText(f'{self.ctx.app_data.convf:#.4f}')
    self.ssde_edit.setText(f'{self.ctx.app_data.SSDE:#.4f}')
    self.dlpc_edit.setText(f'{self.ctx.app_data.DLPc:#.4f}')
    self.effdose_edit.setText(f'{self.ctx.app_data.effdose:#.4f}')
