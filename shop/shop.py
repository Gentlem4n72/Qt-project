import sqlite3
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
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
        result = cur.execute('''SELECT login, password FROM staff
                                    WHERE login = ? AND password = ?''', (login, password)).fetchone()
        accounts.close()

        if (login, password) == result:
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
        self.display()

        self.connection = sqlite3.connect("shop_db.sqlite")
        self.search()

        self.newOrderButton.clicked.connect(self.new_order)
        self.cancelButton.clicked.connect(self.cancel)
        self.formButton.clicked.connect(self.form)
        self.dbTableWidget.cellChanged.connect(self.current_amount_sum)
        self.searchLine.textChanged.connect(self.search)

    def form(self):
        pass

    def new_order(self):
        pass

    def cancel(self):
        pass

    def current_amount_sum(self):
        self.current_amount = 0
        self.current_sum = 0.0
        for i in range(self.dbTableWidget.rowCount()):
            if (self.dbTableWidget.item(i, 2) is None or
                    self.dbTableWidget.item(i, 1) is None):
                return
            amount, price = int(self.dbTableWidget.item(i, 2).text()), float(self.dbTableWidget.item(i, 1).text())
            self.current_amount += amount
            self.current_sum += price * amount
        self.display()

    def display(self):
        self.amountLine.setText(str(self.current_amount))
        self.resultSumLine.setText(str(self.current_sum))

    def search(self):
        request = f'%{self.searchLine.text()}%'
        res = self.connection.cursor().execute('''SELECT name, price, quantity FROM items
                                                    WHERE name LIKE ?''', (request,)).fetchall()

        self.dbTableWidget.setColumnCount(3)
        self.dbTableWidget.setRowCount(0)

        self.dbTableWidget.setHorizontalHeaderLabels(('Название', 'Цена', 'Количество'))
        horizontal_h = self.dbTableWidget.horizontalHeader()
        horizontal_h.resizeSection(0, 274)
        horizontal_h.resizeSection(2, 80)

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
