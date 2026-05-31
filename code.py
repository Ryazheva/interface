import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import psycopg2
from psycopg2 import OperationalError


# ===================== ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ =====================

class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.connection = psycopg2.connect(
                host="localhost",
                port="5432",
                database="postgres",
                user="postgres",
                password="0000"
            )
            self.connection.set_client_encoding('UTF8')
            print("✅ Подключение к базе данных установлено")
        except OperationalError as e:
            print(f"❌ Ошибка подключения: {e}")
            messagebox.showerror("Ошибка", f"Не удалось подключиться к базе данных!\n\n{e}")
            raise e

    def execute_query(self, query, params=None):
        """Выполняет запрос и возвращает результат для SELECT"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                self.connection.commit()
                cursor.close()
                return None
        except Exception as e:
            self.connection.rollback()
            print(f"Ошибка: {e}")
            raise e

    def close(self):
        if self.connection:
            self.connection.close()


# Создаём глобальный объект базы данных
db = Database()


# ===================== ФУНКЦИИ РАБОТЫ С БАЗОЙ =====================

def get_writer_name(writer_id):
    """Возвращает ФИО писателя по ID"""
    result = db.execute_query(
        'SELECT "фамилия", "имя", "отчество" FROM "Литература"."Писатели" WHERE "id_писателя" = %s',
        (writer_id,)
    )
    if result:
        w = result[0]
        patronymic = f" {w[2]}" if w[2] else ""
        return f"{w[0]} {w[1]}{patronymic}"
    return "Неизвестный писатель"


def get_writer_by_id(writer_id):
    """Возвращает кортеж писателя по ID"""
    result = db.execute_query("""
        SELECT p."id_писателя", p."фамилия", p."имя", p."отчество", 
               p."дата рождения", p."дата смерти", c."название" as страна
        FROM "Литература"."Писатели" p
        LEFT JOIN "Литература"."Страны" c ON p."id_страны" = c."id_страны"
        WHERE p."id_писателя" = %s
    """, (writer_id,))
    if result:
        return result[0]
    return None


def get_all_writers():
    """Возвращает всех писателей"""
    return db.execute_query("""
        SELECT p."id_писателя", p."фамилия", p."имя", p."отчество", 
               p."дата рождения", p."дата смерти", c."название" as страна
        FROM "Литература"."Писатели" p
        LEFT JOIN "Литература"."Страны" c ON p."id_страны" = c."id_страны"
        ORDER BY p."фамилия"
    """)


def get_all_works():
    """Возвращает все произведения с информацией о писателе"""
    return db.execute_query("""
        SELECT w."id_произведения", w."название", w."год написания", w."год первого опубликования",
               w."id_писателя"
        FROM "Литература"."Произведения" w
        ORDER BY w."название"
    """)


def get_work_genres(work_id):
    """Возвращает список жанров произведения"""
    result = db.execute_query("""
        SELECT ж."название"
        FROM "Литература"."Жанры произведений" жп
        JOIN "Литература"."Жанры" ж ON жп."id_жанра" = ж."id_жанра"
        WHERE жп."id_произведения" = %s
    """, (work_id,))
    return [row[0] for row in result] if result else []


def get_work_holder(work_id):
    """Возвращает информацию о хранителе произведения"""
    result = db.execute_query("""
        SELECT w."id_организации", w."id_частного лица",
               o."название" as org_name, o."контакты" as org_contacts,
               ч."фамилия", ч."имя", ч."отчество"
        FROM "Литература"."Произведения" w
        LEFT JOIN "Литература"."Организация" o ON w."id_организации" = o."id_организации"
        LEFT JOIN "Литература"."Частное лицо" ч ON w."id_частного лица" = ч."id_частного лица"
        WHERE w."id_произведения" = %s
    """, (work_id,))
    if result:
        row = result[0]
        if row[0]:  # организация
            return f"Организация: {row[2]}"
        elif row[1]:  # частное лицо
            patronymic = f" {row[6]}" if row[6] else ""
            return f"Частное лицо: {row[4]} {row[5]}{patronymic}"
    return "Не указан"


def get_all_countries():
    """Возвращает список всех стран"""
    result = db.execute_query('SELECT "название" FROM "Литература"."Страны" ORDER BY "название"')
    return [row[0] for row in result] if result else []


def get_all_genres():
    """Возвращает список всех жанров"""
    result = db.execute_query('SELECT "id_жанра", "название" FROM "Литература"."Жанры" ORDER BY "название"')
    return result if result else []


def get_all_organizations():
    """Возвращает список организаций"""
    return db.execute_query('SELECT "id_организации", "название" FROM "Литература"."Организация"')


def get_all_private_persons():
    """Возвращает список частных лиц"""
    return db.execute_query('SELECT "id_частного лица", "фамилия", "имя", "отчество" FROM "Литература"."Частное лицо"')


def add_writer_db(surname, name, patronymic, birth_date, death_date, country_name):
    """Добавляет нового писателя в БД"""
    # Получаем id страны
    country_id = None
    if country_name:
        country_result = db.execute_query(
            'SELECT "id_страны" FROM "Литература"."Страны" WHERE "название" = %s',
            (country_name,)
        )
        if country_result:
            country_id = country_result[0][0]

    result = db.execute_query("""
        INSERT INTO "Литература"."Писатели" 
        ("фамилия", "имя", "отчество", "дата рождения", "дата смерти", "id_страны")
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING "id_писателя"
    """, (surname, name, patronymic if patronymic else None,
          birth_date if birth_date else None,
          death_date if death_date else None, country_id))
    return result[0][0] if result else None


def update_writer_db(writer_id, surname, name, patronymic, birth_date, death_date, country_name):
    """Обновляет данные писателя"""
    country_id = None
    if country_name:
        country_result = db.execute_query(
            'SELECT "id_страны" FROM "Литература"."Страны" WHERE "название" = %s',
            (country_name,)
        )
        if country_result:
            country_id = country_result[0][0]

    db.execute_query("""
        UPDATE "Литература"."Писатели" 
        SET "фамилия" = %s, "имя" = %s, "отчество" = %s, 
            "дата рождения" = %s, "дата смерти" = %s, "id_страны" = %s
        WHERE "id_писателя" = %s
    """, (surname, name, patronymic if patronymic else None,
          birth_date if birth_date else None,
          death_date if death_date else None, country_id, writer_id))


def delete_writer_db(writer_id):
    """Удаляет писателя из БД"""
    db.execute_query('DELETE FROM "Литература"."Писатели" WHERE "id_писателя" = %s', (writer_id,))


def add_work_db(title, writer_id, year_written, year_published, org_id, person_id):
    """Добавляет новое произведение в БД"""
    result = db.execute_query("""
        INSERT INTO "Литература"."Произведения" 
        ("название", "id_писателя", "год написания", "год первого опубликования", 
         "id_организации", "id_частного лица")
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING "id_произведения"
    """, (title, writer_id, year_written if year_written else None,
          year_published if year_published else None, org_id, person_id))
    return result[0][0] if result else None


def add_work_genre_db(work_id, genre_id):
    """Добавляет связь произведения с жанром"""
    db.execute_query("""
        INSERT INTO "Литература"."Жанры произведений" ("id_произведения", "id_жанра")
        VALUES (%s, %s)
    """, (work_id, genre_id))


def delete_work_db(work_id):
    """Удаляет произведение из БД"""
    db.execute_query('DELETE FROM "Литература"."Жанры произведений" WHERE "id_произведения" = %s', (work_id,))
    db.execute_query('DELETE FROM "Литература"."Произведения" WHERE "id_произведения" = %s', (work_id,))


def get_statistics_data():
    """Получает статистику из БД"""
    # Количество писателей
    writers_count = db.execute_query('SELECT COUNT(*) FROM "Литература"."Писатели"')
    writers_count = writers_count[0][0] if writers_count else 0

    # Количество произведений
    works_count = db.execute_query('SELECT COUNT(*) FROM "Литература"."Произведения"')
    works_count = works_count[0][0] if works_count else 0

    # Писатели по странам
    writers_by_country = db.execute_query("""
        SELECT c."название", COUNT(*) 
        FROM "Литература"."Писатели" p
        LEFT JOIN "Литература"."Страны" c ON p."id_страны" = c."id_страны"
        GROUP BY c."название"
        ORDER BY COUNT(*) DESC
    """)

    # Произведения по жанрам
    works_by_genre = db.execute_query("""
        SELECT ж."название", COUNT(*) 
        FROM "Литература"."Жанры произведений" жп
        JOIN "Литература"."Жанры" ж ON жп."id_жанра" = ж."id_жанра"
        GROUP BY ж."название"
        ORDER BY COUNT(*) DESC
    """)

    # Произведения по писателям
    works_by_writer = db.execute_query("""
        SELECT п."фамилия", п."имя", COUNT(*) 
        FROM "Литература"."Произведения" пр
        JOIN "Литература"."Писатели" п ON пр."id_писателя" = п."id_писателя"
        GROUP BY п."фамилия", п."имя"
        ORDER BY COUNT(*) DESC
    """)

    return {
        'writers_count': writers_count,
        'works_count': works_count,
        'writers_by_country': writers_by_country if writers_by_country else [],
        'works_by_genre': works_by_genre if works_by_genre else [],
        'works_by_writer': works_by_writer if works_by_writer else []
    }


# ===================== ГЛАВНОЕ ОКНО =====================

root = tk.Tk()
root.title("Информационная система «Литературный архив»")
root.geometry("1300x750")
root.configure(bg='#f0f0f0')

label_status = tk.Label(root, text="Готов к работе", bd=1, relief=tk.SUNKEN, anchor=tk.W)
label_status.pack(side=tk.BOTTOM, fill=tk.X)

notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


# ===================== ВКЛАДКА 1: ПИСАТЕЛИ =====================

tab_writers = ttk.Frame(notebook)
notebook.add(tab_writers, text="📚 Писатели")

# Поиск
search_frame_w = tk.Frame(tab_writers)
search_frame_w.pack(fill=tk.X, padx=10, pady=5)

tk.Label(search_frame_w, text="Поиск:").pack(side=tk.LEFT, padx=5)
search_entry_w = tk.Entry(search_frame_w, width=30)
search_entry_w.pack(side=tk.LEFT, padx=5)


def search_writers():
    search_text = search_entry_w.get().lower()
    writers = get_all_writers()
    for row in tree_writers.get_children():
        tree_writers.delete(row)
    for writer in writers:
        if (search_text in (writer[1] or '').lower() or
                search_text in (writer[2] or '').lower() or
                search_text in (writer[6] or '').lower()):
            tree_writers.insert('', tk.END, values=writer)
    label_status.config(text=f"Найдено: {len(tree_writers.get_children())}")


def reset_writers():
    search_entry_w.delete(0, tk.END)
    load_writers()


btn_search_w = tk.Button(search_frame_w, text="🔍 Искать", command=search_writers, bg='#2196F3', fg='white')
btn_search_w.pack(side=tk.LEFT, padx=5)
btn_reset_w = tk.Button(search_frame_w, text="🔄 Сброс", command=reset_writers, bg='#9E9E9E', fg='white')
btn_reset_w.pack(side=tk.LEFT, padx=5)

# Таблица
frame_writers = tk.Frame(tab_writers)
frame_writers.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

columns_writers = ('id', 'фамилия', 'имя', 'отчество', 'дата_рождения', 'дата_смерти', 'страна')
tree_writers = ttk.Treeview(frame_writers, columns=columns_writers, show='headings', height=12)

for col in columns_writers:
    tree_writers.heading(col, text=col.replace('_', ' ').title())

tree_writers.column('id', width=50)
tree_writers.column('фамилия', width=120)
tree_writers.column('имя', width=100)
tree_writers.column('отчество', width=100)
tree_writers.column('дата_рождения', width=100)
tree_writers.column('дата_смерти', width=100)
tree_writers.column('страна', width=100)

scroll_writers = ttk.Scrollbar(frame_writers, orient=tk.VERTICAL, command=tree_writers.yview)
tree_writers.configure(yscrollcommand=scroll_writers.set)
tree_writers.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scroll_writers.pack(side=tk.RIGHT, fill=tk.Y)


def load_writers():
    for row in tree_writers.get_children():
        tree_writers.delete(row)
    writers = get_all_writers()
    for writer in writers:
        tree_writers.insert('', tk.END, values=writer)
    label_status.config(text=f"Писателей: {len(writers)}")


# Добавление писателя
def add_writer():
    countries = get_all_countries()
    win = tk.Toplevel(root)
    win.title("Добавить писателя")
    win.geometry("400x400")
    win.configure(bg='#f0f0f0')

    tk.Label(win, text="Фамилия:", bg='#f0f0f0').pack(pady=5)
    entry_last = tk.Entry(win, width=40)
    entry_last.pack()

    tk.Label(win, text="Имя:", bg='#f0f0f0').pack(pady=5)
    entry_first = tk.Entry(win, width=40)
    entry_first.pack()

    tk.Label(win, text="Отчество (необязательно):", bg='#f0f0f0').pack(pady=5)
    entry_patr = tk.Entry(win, width=40)
    entry_patr.pack()

    tk.Label(win, text="Дата рождения (ГГГГ-ММ-ДД):", bg='#f0f0f0').pack(pady=5)
    entry_birth = tk.Entry(win, width=40)
    entry_birth.pack()

    tk.Label(win, text="Дата смерти (оставьте пустым, если жив):", bg='#f0f0f0').pack(pady=5)
    entry_death = tk.Entry(win, width=40)
    entry_death.pack()

    tk.Label(win, text="Страна:", bg='#f0f0f0').pack(pady=5)
    combo_country = ttk.Combobox(win, values=countries, width=37)
    combo_country.pack()

    def save_writer():
        last = entry_last.get().strip()
        first = entry_first.get().strip()
        if not last or not first:
            messagebox.showerror("Ошибка", "Фамилия и имя обязательны!")
            return

        add_writer_db(
            last, first,
            entry_patr.get().strip() or None,
            entry_birth.get().strip() or None,
            entry_death.get().strip() or None,
            combo_country.get()
        )
        load_writers()
        messagebox.showinfo("Успех", f"Писатель {last} {first} добавлен!")
        win.destroy()

    tk.Button(win, text="Сохранить", command=save_writer, bg='#4CAF50', fg='white', padx=20, pady=5).pack(pady=20)


# Редактирование писателя
def edit_writer():
    selected = tree_writers.selection()
    if not selected:
        messagebox.showwarning("Предупреждение", "Выберите писателя")
        return

    item = tree_writers.item(selected[0])
    writer_id = item['values'][0]
    writer = get_writer_by_id(writer_id)

    if not writer:
        messagebox.showerror("Ошибка", "Писатель не найден")
        return

    countries = get_all_countries()
    win = tk.Toplevel(root)
    win.title("Редактировать писателя")
    win.geometry("400x450")
    win.configure(bg='#f0f0f0')

    tk.Label(win, text="Фамилия:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_last = tk.Entry(win, width=40)
    entry_last.insert(0, writer[1] if writer[1] else '')
    entry_last.pack()

    tk.Label(win, text="Имя:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_first = tk.Entry(win, width=40)
    entry_first.insert(0, writer[2] if writer[2] else '')
    entry_first.pack()

    tk.Label(win, text="Отчество (необязательно):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_patr = tk.Entry(win, width=40)
    entry_patr.insert(0, writer[3] if writer[3] else '')
    entry_patr.pack()

    tk.Label(win, text="Дата рождения (ГГГГ-ММ-ДД):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_birth = tk.Entry(win, width=40)
    entry_birth.insert(0, writer[4] if writer[4] else '')
    entry_birth.pack()

    tk.Label(win, text="Дата смерти (оставьте пустым если жив):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_death = tk.Entry(win, width=40)
    entry_death.insert(0, writer[5] if writer[5] else '')
    entry_death.pack()

    tk.Label(win, text="Страна:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    combo_country = ttk.Combobox(win, values=countries, width=37)
    combo_country.set(writer[6] if writer[6] else (countries[0] if countries else ''))
    combo_country.pack()

    def save_edit():
        last = entry_last.get().strip()
        first = entry_first.get().strip()
        if not last or not first:
            messagebox.showerror("Ошибка", "Фамилия и имя обязательны!")
            return

        update_writer_db(
            writer_id, last, first,
            entry_patr.get().strip() or None,
            entry_birth.get().strip() or None,
            entry_death.get().strip() or None,
            combo_country.get()
        )
        load_writers()
        messagebox.showinfo("Успех", "Данные писателя обновлены!")
        win.destroy()

    btn_frame = tk.Frame(win, bg='#f0f0f0')
    btn_frame.pack(pady=20)
    tk.Button(btn_frame, text="💾 Сохранить", command=save_edit, bg='#4CAF50', fg='white', padx=20, pady=5).pack(
        side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="❌ Отмена", command=win.destroy, bg='#f44336', fg='white', padx=20, pady=5).pack(
        side=tk.LEFT, padx=10)


# Удаление писателя
def delete_writer():
    selected = tree_writers.selection()
    if not selected:
        messagebox.showwarning("Предупреждение", "Выберите писателя")
        return

    item = tree_writers.item(selected[0])
    writer_id = item['values'][0]
    writer_name = f"{item['values'][1]} {item['values'][2]}"

    if messagebox.askyesno("Подтверждение", f"Удалить писателя {writer_name} и все его произведения?"):
        delete_writer_db(writer_id)
        load_writers()
        load_works()
        messagebox.showinfo("Успех", f"Писатель {writer_name} удален")


# Кнопки на вкладке Писатели
btn_frame_w = tk.Frame(tab_writers)
btn_frame_w.pack(fill=tk.X, padx=10, pady=5)

tk.Button(btn_frame_w, text="➕ Добавить", command=add_writer, bg='#4CAF50', fg='white', padx=10, pady=5).pack(
    side=tk.LEFT, padx=5)
tk.Button(btn_frame_w, text="✏️ Редактировать", command=edit_writer, bg='#FF9800', fg='white', padx=10, pady=5).pack(
    side=tk.LEFT, padx=5)
tk.Button(btn_frame_w, text="🗑️ Удалить", command=delete_writer, bg='#f44336', fg='white', padx=10, pady=5).pack(
    side=tk.LEFT, padx=5)


# ===================== ВКЛАДКА 2: ПРОИЗВЕДЕНИЯ =====================

tab_works = ttk.Frame(notebook)
notebook.add(tab_works, text="📖 Произведения")

# Поиск
search_frame_p = tk.Frame(tab_works)
search_frame_p.pack(fill=tk.X, padx=10, pady=5)

tk.Label(search_frame_p, text="Поиск:").pack(side=tk.LEFT, padx=5)
search_entry_p = tk.Entry(search_frame_p, width=30)
search_entry_p.pack(side=tk.LEFT, padx=5)


def search_works():
    search_text = search_entry_p.get().lower()
    works_data = get_all_works()
    for row in tree_works_main.get_children():
        tree_works_main.delete(row)
    for work in works_data:
        writer_name = get_writer_name(work[4])
        if search_text in (work[1] or '').lower() or search_text in writer_name.lower():
            genres_list = get_work_genres(work[0])
            genres_str = ", ".join(genres_list) if genres_list else "Нет"
            holder = get_work_holder(work[0])
            tree_works_main.insert('', tk.END,
                                   values=(work[0], work[1], writer_name, work[2], work[3], genres_str, holder))
    label_status.config(text=f"Найдено: {len(tree_works_main.get_children())}")


def reset_works():
    search_entry_p.delete(0, tk.END)
    load_works()


btn_search_p = tk.Button(search_frame_p, text="🔍 Искать", command=search_works, bg='#2196F3', fg='white')
btn_search_p.pack(side=tk.LEFT, padx=5)
btn_reset_p = tk.Button(search_frame_p, text="🔄 Сброс", command=reset_works, bg='#9E9E9E', fg='white')
btn_reset_p.pack(side=tk.LEFT, padx=5)

# Таблица
frame_works = tk.Frame(tab_works)
frame_works.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

columns_works_main = ('id', 'название', 'писатель', 'год_написания', 'год_публикации', 'жанры', 'хранитель')
tree_works_main = ttk.Treeview(frame_works, columns=columns_works_main, show='headings', height=12)

for col in columns_works_main:
    tree_works_main.heading(col, text=col.replace('_', ' ').title())

tree_works_main.column('id', width=50)
tree_works_main.column('название', width=200)
tree_works_main.column('писатель', width=150)
tree_works_main.column('год_написания', width=80)
tree_works_main.column('год_публикации', width=80)
tree_works_main.column('жанры', width=150)
tree_works_main.column('хранитель', width=200)

scroll_works_main = ttk.Scrollbar(frame_works, orient=tk.VERTICAL, command=tree_works_main.yview)
tree_works_main.configure(yscrollcommand=scroll_works_main.set)
tree_works_main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scroll_works_main.pack(side=tk.RIGHT, fill=tk.Y)


def load_works():
    for row in tree_works_main.get_children():
        tree_works_main.delete(row)
    works_data = get_all_works()
    for work in works_data:
        writer_name = get_writer_name(work[4])
        genres_list = get_work_genres(work[0])
        genres_str = ", ".join(genres_list) if genres_list else "Нет"
        holder = get_work_holder(work[0])
        tree_works_main.insert('', tk.END,
                               values=(work[0], work[1], writer_name, work[2], work[3], genres_str, holder))
    label_status.config(text=f"Произведений: {len(works_data)}")


# Добавление произведения
def add_work():
    writers_data = get_all_writers()
    genres_data = get_all_genres()
    organizations_data = get_all_organizations()
    persons_data = get_all_private_persons()

    win = tk.Toplevel(root)
    win.title("Добавить произведение")
    win.geometry("550x700")
    win.configure(bg='#f0f0f0')

    tk.Label(win, text="Название:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_title = tk.Entry(win, width=50)
    entry_title.pack()

    tk.Label(win, text="Писатель:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    writer_list = [f"{w[0]} - {w[1]} {w[2]}" for w in writers_data]
    combo_writer = ttk.Combobox(win, values=writer_list, width=47)
    combo_writer.pack()

    tk.Label(win, text="Год написания:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_year_w = tk.Entry(win, width=50)
    entry_year_w.pack()

    tk.Label(win, text="Год публикации (необязательно):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_year_p = tk.Entry(win, width=50)
    entry_year_p.pack()

    tk.Label(win, text="Жанры (можно выбрать несколько):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)

    genres_frame = tk.Frame(win, bg='#f0f0f0')
    genres_frame.pack(pady=5)

    genre_vars = {}
    for i, genre in enumerate(genres_data):
        var = tk.BooleanVar()
        genre_vars[genre[1]] = var
        cb = tk.Checkbutton(genres_frame, text=genre[1], variable=var, bg='#f0f0f0')
        cb.grid(row=i // 2, column=i % 2, padx=10, pady=2, sticky='w')

    tk.Label(win, text="Хранитель (выберите один вариант):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)

    holder_type = tk.StringVar(value="none")

    radio_frame = tk.Frame(win, bg='#f0f0f0')
    radio_frame.pack(pady=5)

    tk.Radiobutton(radio_frame, text="Нет хранителя", variable=holder_type, value="none", bg='#f0f0f0').pack(
        side=tk.LEFT, padx=10)
    tk.Radiobutton(radio_frame, text="Организация", variable=holder_type, value="org", bg='#f0f0f0').pack(side=tk.LEFT,
                                                                                                          padx=10)
    tk.Radiobutton(radio_frame, text="Частное лицо", variable=holder_type, value="person", bg='#f0f0f0').pack(
        side=tk.LEFT, padx=10)

    org_frame = tk.Frame(win, bg='#f0f0f0')
    org_frame.pack(pady=5)
    tk.Label(org_frame, text="Выберите организацию:", bg='#f0f0f0').pack()
    combo_org = ttk.Combobox(org_frame, values=[f"{o[0]} - {o[1]}" for o in organizations_data], width=45)
    combo_org.pack()
    org_frame.pack_forget()

    person_frame = tk.Frame(win, bg='#f0f0f0')
    person_frame.pack(pady=5)
    tk.Label(person_frame, text="Выберите частное лицо:", bg='#f0f0f0').pack()
    person_list = [f"{p[0]} - {p[1]} {p[2]} {p[3] if p[3] else ''}" for p in persons_data]
    combo_person = ttk.Combobox(person_frame, values=person_list, width=45)
    combo_person.pack()
    person_frame.pack_forget()

    def on_holder_type_change(*args):
        org_frame.pack_forget()
        person_frame.pack_forget()
        if holder_type.get() == "org":
            org_frame.pack(pady=5)
        elif holder_type.get() == "person":
            person_frame.pack(pady=5)

    holder_type.trace('w', on_holder_type_change)

    def save_work():
        title = entry_title.get().strip()
        if not title:
            messagebox.showerror("Ошибка", "Название обязательно!")
            return

        if not combo_writer.get():
            messagebox.showerror("Ошибка", "Выберите писателя!")
            return

        writer_id = int(combo_writer.get().split(" - ")[0])

        try:
            year_written = int(entry_year_w.get()) if entry_year_w.get() else 0
            if year_written < 0 or year_written > 2025:
                messagebox.showerror("Ошибка", "Год написания должен быть от 0 до 2026!")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Год написания должен быть числом!")
            return

        try:
            year_published = int(entry_year_p.get()) if entry_year_p.get() else None
            if year_published and (year_published < 0 or year_published > 2025):
                messagebox.showerror("Ошибка", "Год публикации должен быть от 0 до 2026!")
                return
            if year_published and year_published < year_written:
                messagebox.showerror("Ошибка", "Год публикации не может быть раньше года написания!")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Год публикации должен быть числом!")
            return

        selected_genres = [genre[1] for genre in genres_data if genre_vars.get(genre[1], tk.BooleanVar()).get()]
        if not selected_genres:
            messagebox.showerror("Ошибка", "Выберите хотя бы один жанр!")
            return

        org_id = None
        person_id = None

        if holder_type.get() == "org":
            if not combo_org.get():
                messagebox.showerror("Ошибка", "Выберите организацию-хранителя!")
                return
            org_id = int(combo_org.get().split(" - ")[0])
        elif holder_type.get() == "person":
            if not combo_person.get():
                messagebox.showerror("Ошибка", "Выберите частное лицо-хранителя!")
                return
            person_id = int(combo_person.get().split(" - ")[0])

        new_id = add_work_db(title, writer_id, year_written, year_published, org_id, person_id)

        for genre_name in selected_genres:
            for g in genres_data:
                if g[1] == genre_name:
                    add_work_genre_db(new_id, g[0])
                    break

        load_works()

        holder_text = ""
        if org_id:
            for o in organizations_data:
                if o[0] == org_id:
                    holder_text = f", хранитель: {o[1]}"
        elif person_id:
            for p in persons_data:
                if p[0] == person_id:
                    holder_text = f", хранитель: {p[1]} {p[2]}"

        messagebox.showinfo("Успех",
                            f"Произведение '{title}' добавлено!\nЖанры: {', '.join(selected_genres)}{holder_text}")
        win.destroy()

    tk.Button(win, text="✅ Сохранить", command=save_work, bg='#4CAF50', fg='white', padx=20, pady=5).pack(pady=20)


def update_work_db(work_id, title, writer_id, year_written, year_published, org_id, person_id):
    """Обновляет данные произведения в БД"""
    db.execute_query("""
        UPDATE "Литература"."Произведения" 
        SET "название" = %s, 
            "id_писателя" = %s, 
            "год написания" = %s, 
            "год первого опубликования" = %s, 
            "id_организации" = %s, 
            "id_частного лица" = %s
        WHERE "id_произведения" = %s
    """, (title, writer_id,
          year_written if year_written else None,
          year_published if year_published else None,
          org_id, person_id, work_id))


def delete_work_genres_db(work_id):
    """Удаляет все связи произведения с жанрами"""
    db.execute_query('DELETE FROM "Литература"."Жанры произведений" WHERE "id_произведения" = %s', (work_id,))


def edit_work():
    """Редактирование произведения"""
    selected = tree_works_main.selection()
    if not selected:
        messagebox.showwarning("Предупреждение", "Выберите произведение для редактирования!")
        return

    item = tree_works_main.item(selected[0])
    work_id = item['values'][0]
    work_title = item['values'][1]
    work_writer_name = item['values'][2]
    work_year_written = item['values'][3]
    work_year_published = item['values'][4]

    # Получаем текущие данные из БД
    work_data = db.execute_query("""
        SELECT "id_произведения", "название", "id_писателя", 
               "год написания", "год первого опубликования",
               "id_организации", "id_частного лица"
        FROM "Литература"."Произведения" 
        WHERE "id_произведения" = %s
    """, (work_id,))

    if not work_data:
        messagebox.showerror("Ошибка", "Произведение не найдено!")
        return

    work = work_data[0]
    current_writer_id = work[2]
    current_org_id = work[5]
    current_person_id = work[6]

    # Получаем текущие жанры произведения
    current_genres = get_work_genres(work_id)

    # Загружаем данные для форм
    writers_data = get_all_writers()
    genres_data = get_all_genres()
    organizations_data = get_all_organizations()
    persons_data = get_all_private_persons()

    win = tk.Toplevel(root)
    win.title("✏️ Редактировать произведение")
    win.geometry("550x750")
    win.configure(bg='#f0f0f0')

    # Название
    tk.Label(win, text="Название:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_title = tk.Entry(win, width=50)
    entry_title.insert(0, work[1])
    entry_title.pack()

    # Писатель
    tk.Label(win, text="Писатель:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    writer_list = [f"{w[0]} - {w[1]} {w[2]}" for w in writers_data]
    combo_writer = ttk.Combobox(win, values=writer_list, width=47)
    # Устанавливаем текущего писателя
    for w in writer_list:
        if str(current_writer_id) in w.split(" - ")[0]:
            combo_writer.set(w)
            break
    combo_writer.pack()

    # Год написания
    tk.Label(win, text="Год написания:", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_year_w = tk.Entry(win, width=50)
    entry_year_w.insert(0, str(work[3]) if work[3] else '')
    entry_year_w.pack()

    # Год публикации
    tk.Label(win, text="Год публикации (необязательно):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)
    entry_year_p = tk.Entry(win, width=50)
    entry_year_p.insert(0, str(work[4]) if work[4] else '')
    entry_year_p.pack()

    # Жанры
    tk.Label(win, text="Жанры (можно выбрать несколько):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)

    genres_frame = tk.Frame(win, bg='#f0f0f0')
    genres_frame.pack(pady=5)

    genre_vars = {}
    for i, genre in enumerate(genres_data):
        var = tk.BooleanVar()
        # Отмечаем текущие жанры
        if genre[1] in current_genres:
            var.set(True)
        genre_vars[genre[1]] = var
        cb = tk.Checkbutton(genres_frame, text=genre[1], variable=var, bg='#f0f0f0')
        cb.grid(row=i // 2, column=i % 2, padx=10, pady=2, sticky='w')

    # Хранитель
    tk.Label(win, text="Хранитель (выберите один вариант):", bg='#f0f0f0', font=('Arial', 10)).pack(pady=5)

    holder_type = tk.StringVar(value="none")
    if current_org_id:
        holder_type.set("org")
    elif current_person_id:
        holder_type.set("person")
    else:
        holder_type.set("none")

    radio_frame = tk.Frame(win, bg='#f0f0f0')
    radio_frame.pack(pady=5)

    tk.Radiobutton(radio_frame, text="Нет хранителя", variable=holder_type, value="none", bg='#f0f0f0').pack(
        side=tk.LEFT, padx=10)
    tk.Radiobutton(radio_frame, text="Организация", variable=holder_type, value="org", bg='#f0f0f0').pack(side=tk.LEFT,
                                                                                                          padx=10)
    tk.Radiobutton(radio_frame, text="Частное лицо", variable=holder_type, value="person", bg='#f0f0f0').pack(
        side=tk.LEFT, padx=10)

    # Организация
    org_frame = tk.Frame(win, bg='#f0f0f0')
    org_frame.pack(pady=5)
    tk.Label(org_frame, text="Выберите организацию:", bg='#f0f0f0').pack()
    org_values = [f"{o[0]} - {o[1]}" for o in organizations_data] if organizations_data else ["Нет организаций"]
    combo_org = ttk.Combobox(org_frame, values=org_values, width=45)
    if current_org_id:
        for o in org_values:
            if str(current_org_id) in o.split(" - ")[0]:
                combo_org.set(o)
                break
    combo_org.pack()
    org_frame.pack_forget()

    # Частное лицо
    person_frame = tk.Frame(win, bg='#f0f0f0')
    person_frame.pack(pady=5)
    tk.Label(person_frame, text="Выберите частное лицо:", bg='#f0f0f0').pack()
    person_values = [f"{p[0]} - {p[1]} {p[2]} {p[3] if p[3] else ''}" for p in persons_data] if persons_data else [
        "Нет частных лиц"]
    combo_person = ttk.Combobox(person_frame, values=person_values, width=45)
    if current_person_id:
        for p in person_values:
            if str(current_person_id) in p.split(" - ")[0]:
                combo_person.set(p)
                break
    combo_person.pack()
    person_frame.pack_forget()

    def on_holder_type_change(*args):
        org_frame.pack_forget()
        person_frame.pack_forget()
        if holder_type.get() == "org":
            org_frame.pack(pady=5)
        elif holder_type.get() == "person":
            person_frame.pack(pady=5)

    holder_type.trace('w', on_holder_type_change)

    # Показываем текущий выбранный тип хранителя
    if holder_type.get() == "org":
        org_frame.pack(pady=5)
    elif holder_type.get() == "person":
        person_frame.pack(pady=5)

    def save_work_edit():
        title = entry_title.get().strip()
        if not title:
            messagebox.showerror("Ошибка", "Название обязательно!")
            return

        if not combo_writer.get():
            messagebox.showerror("Ошибка", "Выберите писателя!")
            return

        try:
            writer_id = int(combo_writer.get().split(" - ")[0])
        except:
            messagebox.showerror("Ошибка", "Не удалось определить писателя!")
            return

        # Проверка года написания
        year_written = None
        if entry_year_w.get().strip():
            try:
                year_written = int(entry_year_w.get())
                if year_written < 0 or year_written > 2026:
                    messagebox.showerror("Ошибка", "Год написания должен быть от 0 до 2026!")
                    return
            except ValueError:
                messagebox.showerror("Ошибка", "Год написания должен быть числом!")
                return

        # Проверка года публикации
        year_published = None
        if entry_year_p.get().strip():
            try:
                year_published = int(entry_year_p.get())
                if year_published < 0 or year_published > 2026:
                    messagebox.showerror("Ошибка", "Год публикации должен быть от 0 до 2026!")
                    return
                if year_written and year_published < year_written:
                    messagebox.showerror("Ошибка", "Год публикации не может быть раньше года написания!")
                    return
            except ValueError:
                messagebox.showerror("Ошибка", "Год публикации должен быть числом!")
                return

        # Проверка выбора жанров
        selected_genres = []
        for genre_name, var in genre_vars.items():
            if var.get():
                selected_genres.append(genre_name)

        if not selected_genres:
            messagebox.showerror("Ошибка", "Выберите хотя бы один жанр!")
            return

        # Проверка хранителя
        org_id = None
        person_id = None

        if holder_type.get() == "org":
            if not combo_org.get() or combo_org.get() == "Нет организаций":
                messagebox.showerror("Ошибка", "Выберите организацию-хранителя!")
                return
            try:
                org_id = int(combo_org.get().split(" - ")[0])
            except:
                messagebox.showerror("Ошибка", "Не удалось определить организацию!")
                return
        elif holder_type.get() == "person":
            if not combo_person.get() or combo_person.get() == "Нет частных лиц":
                messagebox.showerror("Ошибка", "Выберите частное лицо-хранителя!")
                return
            try:
                person_id = int(combo_person.get().split(" - ")[0])
            except:
                messagebox.showerror("Ошибка", "Не удалось определить частное лицо!")
                return

        # Обновляем произведение
        update_work_db(work_id, title, writer_id, year_written, year_published, org_id, person_id)

        # Обновляем жанры (удаляем старые и добавляем новые)
        delete_work_genres_db(work_id)
        for genre_name in selected_genres:
            for g in genres_data:
                if g[1] == genre_name:
                    add_work_genre_db(work_id, g[0])
                    break

        load_works()
        messagebox.showinfo("Успех", f"Произведение '{title}' успешно обновлено!")
        win.destroy()

    tk.Button(win, text="💾 Сохранить изменения", command=save_work_edit,
              bg='#4CAF50', fg='white', padx=20, pady=5).pack(pady=20)

def delete_work():
    selected = tree_works_main.selection()
    if not selected:
        messagebox.showwarning("Предупреждение", "Выберите произведение")
        return

    item = tree_works_main.item(selected[0])
    work_id = item['values'][0]
    work_title = item['values'][1]

    if messagebox.askyesno("Подтверждение", f"Удалить произведение {work_title}?"):
        delete_work_db(work_id)
        load_works()
        messagebox.showinfo("Успех", f"Произведение {work_title} удалено")


btn_frame_p = tk.Frame(tab_works)
btn_frame_p.pack(fill=tk.X, padx=10, pady=5)

tk.Button(btn_frame_p, text="➕ Добавить", command=add_work, bg='#4CAF50', fg='white', padx=10, pady=5).pack(
    side=tk.LEFT, padx=5)
tk.Button(btn_frame_p, text="✏️ Редактировать", command=edit_work, bg='#FF9800', fg='white', padx=10, pady=5).pack(
    side=tk.LEFT, padx=5)
tk.Button(btn_frame_p, text="🗑️ Удалить", command=delete_work, bg='#f44336', fg='white', padx=10, pady=5).pack(
    side=tk.LEFT, padx=5)
# ===================== ВКЛАДКА 3: СТАТИСТИКА =====================

tab_stats = ttk.Frame(notebook)
notebook.add(tab_stats, text="📊 Статистика")

frame_stats = tk.Frame(tab_stats)
frame_stats.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

stats_text = scrolledtext.ScrolledText(frame_stats, wrap=tk.WORD, width=80, height=20, font=('Courier', 10))
stats_text.pack(fill=tk.BOTH, expand=True)


def load_stats():
    stats_text.delete(1.0, tk.END)
    data = get_statistics_data()

    stats_text.insert(tk.END, "╔══════════════════════════════════════════════════════════════════════════════════╗\n")
    stats_text.insert(tk.END, "║                         СТАТИСТИКА ЛИТЕРАТУРНОГО АРХИВА                          ║\n")
    stats_text.insert(tk.END,
                      "╚══════════════════════════════════════════════════════════════════════════════════╝\n\n")

    stats_text.insert(tk.END, "📊 1. ПИСАТЕЛИ ПО СТРАНАМ:\n")
    stats_text.insert(tk.END, "   " + "─" * 40 + "\n")
    for row in data['writers_by_country']:
        country = row[0] if row[0] else "Не указана"
        count = row[1]
        stats_text.insert(tk.END, f"   • {country}: {count} писатель(ей)\n")

    stats_text.insert(tk.END, "\n")

    stats_text.insert(tk.END, "📊 2. ПРОИЗВЕДЕНИЯ ПО ЖАНРАМ:\n")
    stats_text.insert(tk.END, "   " + "─" * 40 + "\n")
    for row in data['works_by_genre']:
        stats_text.insert(tk.END, f"   • {row[0]}: {row[1]} произведений\n")

    stats_text.insert(tk.END, "\n")

    stats_text.insert(tk.END, "📊 3. ПРОИЗВЕДЕНИЯ ПО ПИСАТЕЛЯМ:\n")
    stats_text.insert(tk.END, "   " + "─" * 40 + "\n")
    for row in data['works_by_writer']:
        writer_name = f"{row[0]} {row[1]}"
        stats_text.insert(tk.END, f"   • {writer_name}: {row[2]} произведений\n")

    stats_text.insert(tk.END, "\n")

    stats_text.insert(tk.END, "📊 4. ОБЩАЯ СТАТИСТИКА:\n")
    stats_text.insert(tk.END, "   " + "─" * 40 + "\n")
    stats_text.insert(tk.END, f"   • Всего писателей: {data['writers_count']}\n")
    stats_text.insert(tk.END, f"   • Всего произведений: {data['works_count']}\n")

    label_status.config(text="Статистика обновлена")


btn_refresh_stats = tk.Button(tab_stats, text="🔄 Показать статистику", command=load_stats, bg='#FF9800', fg='white',
                              padx=10, pady=5)
btn_refresh_stats.pack(pady=10)


# ===================== ЗАПУСК =====================

def on_closing():
    if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
        db.close()
        root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)

load_writers()
load_works()
load_stats()

root.mainloop()
