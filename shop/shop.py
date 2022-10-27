import sys
import sqlite3
import datetime as dt
from docx import Document
from docxtpl import DocxTemplate

from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QFileDialog
from PyQt5.QtSql import QSqlDatabase, QSqlTableModel
from PyQt5 import uic


class Homepage(QMainWindow):
    def __init__(self):
        super(Homepage, self).__init__()
        uic.loadUi('Homepage.ui', self)

        self.mainwindow = Mainwindow()

        self.enterButton.clicked.connect(self.enter)
        self.loginLine.textChanged.connect(self.clear)
        self.passwordLine.textChanged.connect(self.clear)

    def enter(self):
        accounts = sqlite3.connect('shop_db.sqlite')
        cur = accounts.cursor()
        login, password = self.loginLine.text(), self.passwordLine.text()
        result = cur.execute('''SELECT name, login, password FROM staff
                                    WHERE login = ? AND password = ?''', (login, password)).fetchone()
        accounts.close()

        if (login, password) == result[1:]:
            self.mainwindow.cashier = result[0]
            self.mainwindow.show()
            homepage.close()
        else:
            self.errorLabel.setText('Не удалось найти аккаунт с данными логином и паролем')

    def clear(self):
        self.errorLabel.setText('')


class Mainwindow(QMainWindow):
    def __init__(self):
        super(Mainwindow, self).__init__()
        uic.loadUi('Mainwindow.ui', self)

        self.current_amount = 0
        self.current_sum = 0.0
        self.order = {}
        self.overall_discount = 0
        self.cashier = ''

        self.fname = 'check.docx'

        self.connection = sqlite3.connect("shop_db.sqlite")
        self.cursor = self.connection.cursor()
        self.search()

        self.newOrderButton.clicked.connect(self.new_order)
        self.cancelButton.clicked.connect(self.cancel)
        self.formButton.clicked.connect(self.form)
        self.dbTableWidget.cellChanged.connect(self.current_amount_sum)
        self.searchLine.textChanged.connect(self.search)
        self.saveFilePathButton.clicked.connect(self.select_path)

    def form(self):
        template = DocxTemplate('check_template.docx')
        data = {
            'items': ['    '.join(map(str, x[:2])) + '\n'
                      + '                    '.join(map(str, x[2:]))
                      for x in self.order.values()],
            'discount': self.overall_discount,
            'total': self.current_sum,
            'cashier': self.cashier,
            'date': dt.date.today(),
            'time': dt.datetime.now().strftime("%H:%M")
        }
        template.render(data)
        template.save(self.fname)

        text = []
        for par in Document(self.fname).paragraphs:
            text.append(par.text)
        self.checkPreviewText.setText('\n'.join(text))

    def select_path(self):
        self.fname = QFileDialog.getSaveFileName(self, 'Выбрать путь сохранения', 'check.docx')[0]

    def new_order(self):
        self.form()
        self.cancel()

    def cancel(self):
        self.order = {}
        self.overall_discount = 0
        self.cursor.execute('''UPDATE items SET quantity = 0''')
        self.searchLine.setText('')
        self.search()
        self.checkPreviewText.clear()
        self.fname = 'check.docx'

    def current_amount_sum(self):
        for i in range(self.dbTableWidget.rowCount()):
            if self.dbTableWidget.item(i, 4) is None:
                return
            id, name, price, discount, quantity = [self.dbTableWidget.item(i, x).text() for x in range(5)]
            id, name, price, discount, quantity = int(id), name.upper(), float(price), int(discount), int(quantity)
            if quantity == 0 or (name in self.order and quantity == self.order[name][4]):
                continue
            total = round(quantity * price * (100 - discount) / 100, 2)
            discount = '       ' if discount == 0 else str(discount) + '%'
            self.order[name] = (id, name, price, discount, quantity, total)
            self.overall_discount += round(quantity * price - total, 2)
            self.cursor.execute('''UPDATE items
                                    SET quantity = ?
                                    WHERE id = ?''', (quantity, id))
        self.current_amount = sum(x[1][4] for x in self.order.items())
        self.current_sum = round(sum(x[1][5] for x in self.order.items()), 2)
        self.amountLine.setText(str(self.current_amount))
        self.resultSumLine.setText(str(self.current_sum))

    def search(self):
        request = f'%{self.searchLine.text()}%'
        res = self.cursor.execute('''SELECT * FROM items
                                                    WHERE name LIKE ?''', (request,)).fetchall()

        self.dbTableWidget.setColumnCount(5)
        self.dbTableWidget.setRowCount(0)

        self.dbTableWidget.setHorizontalHeaderLabels(('ID', 'Название', 'Цена', 'Cкидка', 'Количество'))
        horizontal_h = self.dbTableWidget.horizontalHeader()
        horizontal_h.resizeSection(0, 30)
        horizontal_h.resizeSection(1, 265)
        horizontal_h.resizeSection(2, 80)
        horizontal_h.resizeSection(3, 80)
        horizontal_h.resizeSection(4, 80)

        for i, row in enumerate(res):
            self.dbTableWidget.setRowCount(
                self.dbTableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.dbTableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))

    def closeEvent(self, event):
        self.connection.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    homepage = Homepage()
    homepage.show()
    sys.exit(app.exec())
