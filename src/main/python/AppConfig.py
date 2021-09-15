import json
import os
import sys
from PyQt5.QtCore import Qt

from PyQt5.QtGui import QIcon
from PyQt5.QtSql import QSqlTableModel
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QRadioButton, QStackedLayout, QStackedWidget, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from db import create_patients_table


class AppConfig(QDialog):
  def __init__(self, ctx):
    super(AppConfig, self).__init__()
    self.ctx = ctx

    self.add_scanner_dlg = ScannerDataDialog(self.ctx, parent=self)
    btns = QDialogButtonBox.RestoreDefaults | QDialogButtonBox.Save | QDialogButtonBox.Cancel
    self.buttons = QDialogButtonBox(btns)

    self.setWindowTitle("Settings")
    self.layout = QVBoxLayout()
    self.tabs = QTabWidget()
    self.setTabs()

    try:
      self.configs = self._get_config()
    except:
      self._set_default()

    self.layout.addWidget(self.tabs)
    self.layout.addWidget(self.buttons)

    self.patients_db.setText(os.path.abspath(self.configs['patients_db']))
    self.setLayout(self.layout)
    self.resize(400, 300)

  def setConnect(self):
    self.buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.on_restore)
    self.buttons.accepted.connect(self.on_save)
    self.buttons.rejected.connect(self.on_cancel)
    self.open_db.clicked.connect(self.on_open)
    self.add_scanner_btn.clicked.connect(self.on_scanner_data)

  def setTabs(self):
    self.db_tab = QWidget()
    grid = QVBoxLayout()

    self.patients_db = QLineEdit()
    self.patients_db.setMinimumWidth(400)
    self.open_db = QPushButton(self.ctx.save_icon, '')

    pat_data_grpbox = QGroupBox('Patients Records Database:')
    h = QHBoxLayout()
    h.addWidget(self.patients_db)
    h.addWidget(self.open_db)
    h.addStretch()
    pat_data_grpbox.setLayout(h)

    self.add_scanner_btn = QPushButton('Add Scanner Data')
    scanner_data_grpbox = QGroupBox('Scanner Database:')
    h2 = QHBoxLayout()
    h2.addWidget(self.add_scanner_btn)
    h2.addStretch()
    scanner_data_grpbox.setLayout(h2)

    grid.addWidget(pat_data_grpbox)
    grid.addWidget(scanner_data_grpbox)
    grid.addStretch()

    self.db_tab.setLayout(grid)
    self.tabs.addTab(self.db_tab, 'Database')

    self.setConnect()

  def _get_config(self):
    with open(self.ctx.config_file(), 'r') as f:
      return json.load(f)

  def _set_config(self):
    with open(self.ctx.config_file(), 'w') as f:
      json.dump(self.configs, f, sort_keys=True, indent=4)

  def _set_default(self):
    self.configs = {
      'patients_db': self.ctx.default_patients_database,
    }
    self._set_config()
    if not os.path.exists(self.configs['patients_db']):
      try:
        create_patients_table(self.configs['patients_db'])
      except:
        self.ctx.ioError()
        return
    self.patients_db.setText(os.path.abspath(self.configs['patients_db']))

  def on_scanner_data(self):
    QMessageBox.information(None, "Not yet implemented", "This feature is not fully implemented yet.")
    acc = self.add_scanner_dlg.exec()

  def on_save(self):
    self.configs['patients_db'] = os.path.abspath(self.patients_db.text())
    self._set_config()

    if not os.path.isfile(self.configs['patients_db']):
      create_patients_table(self.configs['patients_db'])
    self.accept()

  def on_open(self):
    filename, _ = QFileDialog.getSaveFileName(self, "Select Database File", os.path.join(self.configs['patients_db'], os.pardir), "Database (*.db)")
    print(filename)
    if not filename:
      return
    self.patients_db.setText(os.path.abspath(filename))

  def on_restore(self):
    btn_reply = QMessageBox.question(self, 'Restore Default', 'Restore the default settings?')
    if btn_reply == QMessageBox.No:
      return
    self._set_default()
    self.accept()

  def on_cancel(self):
    self.patients_db.setText(os.path.abspath(self.configs['patients_db']))
    self.reject()

class ScannerDataDialog(QDialog):
  def __init__(self, ctx, *args, **kwargs):
    super(ScannerDataDialog, self).__init__(*args, **kwargs)
    self.ctx = ctx
    self.setWindowTitle("Add Scanner Data")
    self.initUI()
    self.initModel()
    self.signal_connect()

  def signal_connect(self):
    self.exist_scanner_chk.stateChanged.connect(self.on_exist_scanner)
    self.exist_brand_chk.stateChanged.connect(self.on_exist_brand)
    self.buttons.accepted.connect(self.on_save)
    self.buttons.rejected.connect(self.on_close)
    self.brand_cb.activated[int].connect(self.on_brand_changed)
    self.scanner_cb.activated[int].connect(self.on_scanner_changed)
    [btn.toggled.connect(self.on_phantom_select) for btn in self.phantom_rbs]

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

    self.brand_cb.setModel(self.brand_query)
    self.brand_cb.setModelColumn(self.brand_query.fieldIndex("NAME"))
    self.scanner_cb.setModel(self.scanner_query)
    self.scanner_cb.setModelColumn(self.scanner_query.fieldIndex("NAME"))

    self.on_brand_changed(0)

  def initUI(self):
    btns = QDialogButtonBox.Save | QDialogButtonBox.Close
    self.buttons = QDialogButtonBox(btns)
    self.brand_cb = QComboBox()
    self.scanner_cb = QComboBox()
    self.brand_edit = QLineEdit()
    self.scanner_edit = QLineEdit()
    self.volt_edit = QLineEdit()
    self.coll_edit = QLineEdit()
    self.ctdih_edit = QTextEdit()
    self.ctdib_edit = QTextEdit()

    self.ctdi_edits_layout = QStackedWidget(self)
    self.ctdi_edits_layout.addWidget(self.ctdih_edit)
    self.ctdi_edits_layout.addWidget(self.ctdib_edit)

    self.phantom_rbs = [QRadioButton('Head'), QRadioButton('Body')]
    self.phantom_rbs[0].setChecked(True)
    self.exist_brand_chk = QCheckBox('Add existing')
    self.exist_scanner_chk = QCheckBox('Add existing')
    self.exist_scanner_chk.setEnabled(False)

    self.brand_edits_layout = QStackedWidget()
    self.brand_edits_layout.addWidget(self.brand_edit)
    self.brand_edits_layout.addWidget(self.brand_cb)
    self.scanner_edits_layout = QStackedWidget()
    self.scanner_edits_layout.addWidget(self.scanner_edit)
    self.scanner_edits_layout.addWidget(self.scanner_cb)

    self.rb_layout = QHBoxLayout()
    [self.rb_layout.addWidget(btn) for btn in self.phantom_rbs]
    self.rb_layout.addStretch()

    self.main_widget = QWidget()
    self.inner_layout = QFormLayout()
    self.inner_layout.addRow(QLabel('Manufacturer'), self.brand_edits_layout)
    self.inner_layout.addRow(QLabel(''), self.exist_brand_chk)
    self.inner_layout.addRow(QLabel('Scanner'), self.scanner_edits_layout)
    self.inner_layout.addRow(QLabel(''), self.exist_scanner_chk)
    self.inner_layout.addRow(QLabel('Voltage'), self.volt_edit)
    self.inner_layout.addRow(QLabel('Collimation'), self.coll_edit)
    self.inner_layout.addRow(QLabel('Phantom'), self.rb_layout)
    self.inner_layout.addRow(QLabel('CTDIw'), self.ctdi_edits_layout)
    self.main_widget.setLayout(self.inner_layout)

    self.main_layout = QVBoxLayout()
    self.main_layout.addWidget(self.main_widget)
    self.main_layout.addWidget(self.buttons)
    self.setLayout(self.main_layout)

    # txt = 'Comma-separated values for each collimation for each '
    # self.ctdib_edit.setPlaceholderText('body')
    # self.ctdih_edit.setPlaceholderText('head')

  def on_exist_brand(self, state):
    self.brand_edits_layout.setCurrentIndex(int(state==Qt.Checked))
    self.exist_scanner_chk.setCheckState(Qt.Unchecked)
    self.exist_scanner_chk.setEnabled(state==Qt.Checked)

  def on_exist_scanner(self, state):
    self.scanner_edits_layout.setCurrentIndex(int(state==Qt.Checked))

  def on_brand_changed(self, sel):
    self.brand_id = self.brand_query.record(sel).value("ID")
    self.scanner_query.setFilter(f"BRAND_ID={self.brand_id}")
    self.on_scanner_changed(0)
    self.scanner_items = [self.scanner_cb.itemText(i).lower() for i in range(self.scanner_cb.count())]

  def on_scanner_changed(self, sel):
    self.scanner_id = self.scanner_query.record(sel).value("ID")
    self.volt_query.setFilter(f"SCANNER_ID={self.scanner_id}")
    self.coll_query.setFilter(f"SCANNER_ID={self.scanner_id}")
    # if self.volt_query.rowCount()>0:
    #   self.volt_items = [float(self.volt_cb.itemText(i)) for i in range(self.volt_cb.count())]
    # if self.coll_query.rowCount()>0:
    #   self.coll_items = [float(self.coll_query.record(i).value("COL_VAL")) for i in range(self.coll_cb.count())]

  def on_phantom_select(self):
    sel = self.sender()
    if sel.isChecked():
      self.phantom = sel.text().lower()
      self.ctdi_edits_layout.setCurrentIndex(int(self.phantom=='body'))

  def on_save(self):
    # crazy stuffs
    btn_reply = QMessageBox.question(self, 'Add more data', 'Do you want to add more data?')
    self.reset_fields()
    if btn_reply == QMessageBox.No:
      self.accept()

  def on_close(self):
    self.reset_fields()
    self.reject()

  def reset_fields(self):
    self.brand_edit.setText('')
    self.scanner_edit.setText('')
    self.volt_edit.setText('')
    self.coll_edit.setText('')
    self.ctdih_edit.setText('')
    self.exist_brand_chk.setCheckState(Qt.Unchecked)
    self.exist_scanner_chk.setCheckState(Qt.Unchecked)
