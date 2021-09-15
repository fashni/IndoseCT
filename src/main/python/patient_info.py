from PyQt5.QtCore import QDate, QRegExp, QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QRegExpValidator, QValidator
from PyQt5.QtWidgets import (QAbstractSpinBox, QComboBox, QDateEdit,
                             QFormLayout, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QRadioButton, QSpinBox, QVBoxLayout,
                             QWidget)


class InfoPanel(QWidget):
  def __init__(self, ctx, *args, **kwargs):
    super(InfoPanel, self).__init__(*args, **kwargs)
    self.ctx = ctx
    self.initVar()
    self.initUI()
    self.sigConnect()
    self.setInfo(self.getInfo())

  def initVar(self):
    self.id = None
    self.name = None
    self.protocol = None
    self.date = QDate.currentDate().toString('yyyyMMdd')
    self.age = -1
    self.sex = None
    self.scanner = None
    self.instn = None

  def sigConnect(self):
    self.name_edit.textChanged.connect(self.on_name_changed)
    self.protocol_edit.textChanged.connect(self.on_protocol_changed)
    self.exam_date_edit.dateChanged.connect(self.on_date_changed)
    self.age_edit.valueChanged.connect(self.on_age_changed)
    self.sex_edit.activated[int].connect(self.on_sex_changed)
    self.scanner_edit.textChanged.connect(self.on_scanner_changed)
    self.instn_edit.textChanged.connect(self.on_instn_changed)
    self.scanner_validator.validationChanged.connect(self.on_scanner_validation)

  def initUI(self):
    self.no_edit = QLineEdit()
    self.name_edit = QLineEdit()
    self.protocol_edit = QLineEdit()
    self.exam_date_edit = QDateEdit()
    self.age_edit = QSpinBox()
    self.sex_edit = QComboBox()
    self.instn_edit = QLineEdit()
    self.scanner_edit = QLineEdit()

    reg_ex = QRegExp('.*\-.*')
    self.scanner_validator = RegExpValidator(reg_ex, self.scanner_edit)

    self.scanner_edit.setValidator(self.scanner_validator)
    self.scanner_edit.setAlignment(Qt.AlignLeft)
    self.scanner_edit.setPlaceholderText('Manufacturer-Model')
    self.sex_edit.addItems(['M', 'F', 'Unspecified'])
    self.sex_edit.setPlaceholderText('Unspecified')
    self.sex_edit.setCurrentIndex(2)
    self.exam_date_edit.setDisplayFormat('dd/MM/yyyy')
    self.exam_date_edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
    self.age_edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
    self.age_edit.setSpecialValueText('-')
    self.age_edit.setMinimum(-1)
    self.age_edit.setValue(-1)

    l_layout = QFormLayout()
    l_layout.setVerticalSpacing(1)
    l_layout.addRow(QLabel('ID'), self.no_edit)
    l_layout.addRow(QLabel('Name'), self.name_edit)
    l_layout.addRow(QLabel('Age'), self.age_edit)
    l_layout.addRow(QLabel('Sex'), self.sex_edit)

    r_layout = QFormLayout()
    r_layout.setVerticalSpacing(1)
    r_layout.addRow(QLabel('Exam Date'), self.exam_date_edit)
    r_layout.addRow(QLabel('Institution'), self.instn_edit)
    r_layout.addRow(QLabel('Scanner'), self.scanner_edit)
    r_layout.addRow(QLabel('Protocol'), self.protocol_edit)

    main_layout = QHBoxLayout()
    main_layout.addLayout(l_layout)
    main_layout.addLayout(r_layout)

    self.setLayout(main_layout)
    self.setMaximumHeight(100)
    self.setContentsMargins(0,0,0,0)

  def setInfo(self, pat_info):
    self.id = pat_info['id'] or ''
    self.name = pat_info['name'] or ''
    self.protocol = pat_info['protocol'] or ''
    self.age = pat_info['age'] or -1
    self.sex = pat_info['sex'] or None
    self.date = pat_info['date'] or None
    self.scanner = pat_info['scanner'] or None
    self.instn = pat_info['instn'] or None
    date = QDate.fromString(self.date, 'yyyyMMdd') if self.date is not None else QDate.currentDate()

    self.no_edit.setText(self.id)
    self.name_edit.setText(self.name)
    self.protocol_edit.setText(self.protocol)
    self.age_edit.setValue(self.age)
    self.sex_edit.setCurrentText(self.sex if self.sex is not None else self.sex_edit.itemText(2))
    self.exam_date_edit.setDate(date)
    self.scanner_edit.setText(self.scanner)
    self.instn_edit.setText(self.instn)

  def getInfo(self):
    brand = model = None
    if self.scanner:
      brand_model = self.scanner.split('-')
      if len(brand_model)==2:
        brand = brand_model[0] or None
        model = brand_model[1] or None
    info = {
      'id': self.id or None,
      'name': self.name or None,
      'sex': self.sex or None,
      'age': self.age if self.age>=0 else None,
      'protocol': self.protocol or None,
      'date': self.date or None,
      'brand': brand,
      'model': model,
      'scanner': self.scanner or None,
      'instn': self.instn or None,
      }
    return info

  def on_name_changed(self):
    self.name = self.name_edit.text()

  def on_date_changed(self):
    self.date = self.exam_date_edit.date().toString('yyyyMMdd')

  def on_age_changed(self):
    self.age = self.age_edit.value()

  def on_sex_changed(self, id):
    self.sex = self.sex_edit.currentText() if id != 2 else None
    print(self.sex)

  def on_protocol_changed(self):
    self.protocol = self.protocol_edit.text()

  def on_instn_changed(self):
    self.instn = self.instn_edit.text()

  def on_scanner_changed(self):
    self.scanner = self.scanner_edit.text()

  def on_scanner_validation(self, state):
    if state == QValidator.Invalid:
      colour = 'red'
    elif state == QValidator.Intermediate:
      colour = 'gold'
    elif state == QValidator.Acceptable:
      colour = 'lime'
    self.scanner_edit.setStyleSheet('border: 3px solid %s' % colour)
    QTimer.singleShot(1000, lambda: self.scanner_edit.setStyleSheet(''))

class RegExpValidator(QRegExpValidator):
  validationChanged = pyqtSignal(QValidator.State)
  def validate(self, inpt, pos):
    state, inpt, pos = super().validate(inpt, pos)
    self.validationChanged.emit(state)
    return state, inpt, pos
