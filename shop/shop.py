import sys
import sqlite3
import datetime as dt
from docx import Document
from docxtpl import DocxTemplate

from PyQt5.QtWidgets import QTableWidgetItem, QFileDialog, QDialog, QMessageBox, QInputDialog
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt
from PyQt5 import uic


class Homepage(QMainWindow):
    # Окно входа в аккаунт сотрудника.
    def __init__(self):
        super(Homepage, self).__init__()
        uic.loadUi('UI/Homepage.ui', self)
        self.setFixedSize(800, 500)

        self.enterButton.clicked.connect(self.enter)
        self.enterButton.setEnabled(False)
        self.loginLine.textChanged.connect(self.clear)
        self.passwordLine.textChanged.connect(self.clear)

    def enter(self):
        #Сопоставляет введенные логин и пароль с логином и паролем из базы данных.
        # При совпадении закрывает это окно и отрывает окно Mainwindow.
        # Иначе выводит сообщение об ошибке.
        accounts = sqlite3.connect('db/shop_db.sqlite')
        cur = accounts.cursor()
        login, password = self.loginLine.text(), self.passwordLine.text()
        result = cur.execute('''SELECT name, post, login, password FROM staff
                                    WHERE login = ? AND password = ?''', (login, password)).fetchone()

        if result is not None and (login, password) == result[2:]:
            mainwindow.cashier = result[0]
            mainwindow.edit_flag = cur.execute('''SELECT title FROM posts
                                                    WHERE postid = ?''', (result[1])).fetchone()[0] == 'менеджер'
            mainwindow.show()
            if not mainwindow.edit_flag:
                mainwindow.addStaffButton.hide()
                mainwindow.addItemButton.hide()
            mainwindow.search()
            homepage.close()
        else:
            self.errorLabel.setText('Не удалось найти аккаунт с данными логином и паролем')

        accounts.close()

    def clear(self):
        #При редактировании одного из полей убирает сообщение об ошибке и
        #делает активной кнопку входа если оба поля не пустые.
        if self.loginLine.text() == '' or self.passwordLine.text() == '':
            self.enterButton.setEnabled(False)
        else:
            self.enterButton.setEnabled(True)
        self.errorLabel.setText('')


class Mainwindow(QMainWindow):
    #Окно составления заказа.
    def __init__(self):
        super(Mainwindow, self).__init__()
        uic.loadUi('UI/Mainwindow.ui', self)
        self.setFixedSize(910, 670)

        self.current_amount = 0
        self.current_sum = 0.0
        self.order = {}
        self.overall_discount = 0

        self.fname = 'check.docx'
        self.edit_flag = False

        self.connection = sqlite3.connect("db/shop_db.sqlite")
        self.cursor = self.connection.cursor()

        self.newOrderButton.clicked.connect(self.new_order)
        self.cancelButton.clicked.connect(self.cancel)
        self.formButton.clicked.connect(self.form)
        self.dbTableWidget.itemChanged.connect(self.current_amount_sum)
        self.searchLine.textChanged.connect(self.search)
        self.saveFilePathButton.clicked.connect(self.select_path)
        self.addItemButton.clicked.connect(self.add_item)
        self.addStaffButton.clicked.connect(self.add_staff)

    def form(self):
        #Формирует чек из заданных товаров в соответствии с шаблоном “check_template.docx”.
        if self.order:
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
        else:
            self.checkPreviewText.setText('Заказ пуст')

    def select_path(self):
        #Выводит диалоговое окно выбора пути сохранения чека.
        self.fname = QFileDialog.getSaveFileName(self, 'Выбрать путь сохранения', 'check.docx')[0]

    def new_order(self):
        #Сохраняет текущий заказ и переходит к новому.
        self.form()
        self.cancel()

    def cancel(self):
        #Отменяет текущий заказ и очищает поле поиска и путь сохранения.
        self.order = {}
        self.overall_discount = 0
        self.cursor.execute('''UPDATE items SET quantity = 0''')
        self.searchLine.clear()
        self.search()
        self.amountLine.setText('0')
        self.resultSumLine.setText('0.0')
        self.checkPreviewText.clear()
        self.fname = 'check.docx'

    def current_amount_sum(self, item):
        #Подсчитывает и выводит промежуточные кол-во товаров и общую стоимость.
        if item.text() == '': #Замена значений пустых ячеек на стандартные
            self.dbTableWidget.setItem(item.row(), item.column(), QTableWidgetItem(
                '0' if item.column() > 1 else 'Безымянный товар'))
            return

        if not all(self.dbTableWidget.item(item.row(), x) for x in range(5)): #Проверка на заполненность всех ячеек
            return

        if item.column() == 4: #Колонка "Количество"
            id, name, price, discount, quantity = (self.dbTableWidget.item(item.row(), x).text() for x in range(5))
            id, name, price, discount, quantity = int(id), name.upper(), float(price), int(discount), int(quantity)
            if quantity == 0 and id in self.order: #Удаление товаров с количеством "0" из заказа
                del self.order[id]
                self.cursor.execute('''UPDATE items
                                                SET quantity = 0
                                                WHERE id = ?''', (id,))
            elif quantity == 0: #Пропуск товаров с количеством "0" в таблице
                return
            else:
                total = round(quantity * price * (100 - discount) / 100, 2)
                discount = '       ' if discount == 0 else str(discount) + '%'
                self.order[id] = (id, name, price, discount, quantity, total)
                self.cursor.execute('''UPDATE items
                                                SET quantity = ?
                                                WHERE id = ?''', (quantity, id))
            self.overall_discount = round(sum(x[1][4] * x[1][2] - x[1][5] for x in self.order.items()), 2)
            self.current_amount = sum(x[1][4] for x in self.order.items())
            self.current_sum = round(sum(x[1][5] for x in self.order.items()), 2)
            self.amountLine.setText(str(self.current_amount))
            self.resultSumLine.setText(str(self.current_sum))
        elif item.column() > 0: #Изменения в остальных колонках (кроме "ID") коммитятся в базу данных
            self.edit(item)

    def edit(self, item):
        #Дублирует изменения в таблице в базу данных.
        id, name, price, discount = (self.dbTableWidget.item(item.row(), x).text() for x in range(4))
        self.cursor.execute('''UPDATE items
                                SET name = ?, price = ?, discount = ?
                                WHERE id = ?''', (name.lower(), price, discount, id))
        self.connection.commit()
        self.current_amount_sum(self.dbTableWidget.item(item.row(), 4))

    def search(self):
        #Производит поиск по названию товара в таблице и выводит результат.
        request = f'%{self.searchLine.text()}%'
        res = self.cursor.execute('''SELECT * FROM items
                                                    WHERE name LIKE ?''', (request,)).fetchall()
        #Конструируем таблицу
        self.dbTableWidget.setColumnCount(5)
        self.dbTableWidget.setRowCount(0)

        self.dbTableWidget.setHorizontalHeaderLabels(('ID', 'Название', 'Цена', 'Cкидка', 'Количество'))
        horizontal_h = self.dbTableWidget.horizontalHeader()
        horizontal_h.resizeSection(0, 30)
        horizontal_h.resizeSection(1, 265)
        horizontal_h.resizeSection(2, 80)
        horizontal_h.resizeSection(3, 56)
        horizontal_h.resizeSection(4, 80)

        for i, row in enumerate(res):
            self.dbTableWidget.setRowCount(
                self.dbTableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.dbTableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem).capitalize()))
                if j == 0 or (not self.edit_flag and j != 4):
                    #Колонка "ID" не подлежит изменению, а изменения колонки "Количество" доступно любому сотруднику
                    self.dbTableWidget.item(i, j).setFlags(
                        self.dbTableWidget.item(i, j).flags() ^ Qt.ItemIsEditable)
    def add_item(self):
        #Добавляет новый товар в базу данных
        dialog = AddItemDialog()
        if dialog.exec():
            name, price, discount = dialog.nameLine.text(), dialog.priceLine.text(), dialog.discountLine.text()
            self.cursor.execute('''INSERT INTO items(name, price, discount, quantity) VALUES(?, ?, ?, 0)''',
                                (name, price, discount))
            self.connection.commit()
            self.search()

    def add_staff(self):
        #Добавляет нового сотрудника в базу данных
        dialog = AddStaffDialog()
        if dialog.exec():
            name, post, login, password = (dialog.nameLine.text(), dialog.postComboBox.currentText(),
                                           dialog.loginLine.text(), dialog.passwordLine.text())
            post_id = self.cursor.execute('''SELECT postid FROM posts
                                                                WHERE title = ?''', (post,)).fetchone()
            if self.cursor.execute('''SELECT * FROM staff
                                        WHERE login = ? AND password = ?''',
                                   (login, password)).fetchone() is None:
                self.cursor.execute('''INSERT INTO staff(name, post, login, password) VALUES(?, ?, ?, ?)''',
                                    (name, *post_id, login, password))
                self.connection.commit()
            else:
                QMessageBox.about(self, 'Ошибка', 'Сотрудник с таким паролем и логином уже существует')

    def closeEvent(self, event):
        #При закрытии приложения возвращаем колонке "Количество" значения 0, коммитим и закрываем базу данных
        self.cursor.execute('''UPDATE items
                                SET quantity = 0''')
        self.connection.commit()
        self.connection.close()


class AddStaffDialog(QDialog):
    #Диалоговое окно добавления нового сотрудника
    def __init__(self):
        super(QDialog, self).__init__()
        uic.loadUi('UI/AddStaffDialog.ui', self)
        self.setWindowTitle('Добавление сотрудника')
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

class AddItemDialog(QDialog):
    # Диалоговое окно добавления нового товара
    def __init__(self):
        super(QDialog, self).__init__()
        uic.loadUi('UI/AddItemDialog.ui', self)
        self.setWindowTitle('Добавление товара')
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    homepage = Homepage()
    mainwindow = Mainwindow()
    homepage.show()
    sys.exit(app.exec())
