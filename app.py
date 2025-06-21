# ==============================================================================
# Стъпка 1: Инсталиране на Taipy и Gunicorn
# Gunicorn е сървърът, който ще използваме, за да работи приложението в Render
# ==============================================================================
print(">>> Инсталиране на необходимите библиотеки...")
!pip install taipy gunicorn &> /dev/null
print(">>> Taipy и Gunicorn са инсталирани успешно.")

# ==============================================================================
# Стъпка 2: Импортиране на необходимите модули
# ==============================================================================
from taipy.gui import Gui, State, notify
import pandas as pd
import os

# ==============================================================================
# Стъпка 3: Дефиниране на пътя до данните
# ==============================================================================
# Тази част е нужна, ако стартирате скрипта в Google Colab
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=True)
    DATA_PATH = '/content/drive/MyDrive/FootballData/_final_dataset/visualization_data.csv'
except ImportError:
    # Ако стартирате локално, поставете файла в същата папка като скрипта
    DATA_PATH = 'visualization_data.csv'

# ==============================================================================
# Стъпка 4: Подготовка на данните и състоянието на приложението
# ==============================================================================
try:
    full_dataset = pd.read_csv(DATA_PATH)
    
    # Създаваме колона с кликаем URL адрес, използвайки Markdown синтаксис
    full_dataset['URL'] = full_dataset.apply(
        lambda row: f"[{row['Home Team']} vs {row['Away Team']}]({row['Match URL']})" if pd.notna(row['Match URL']) else "No Link", 
        axis=1
    )

    # Попълваме липсващите стойности с тирета за по-добра визуализация
    full_dataset.fillna('-', inplace=True)

    countries = ["All"] + sorted(full_dataset['Country'].unique().tolist())
    divisions = ["All"]
    
    predictions_df = full_dataset.copy()
    
except FileNotFoundError:
    print(f"ГРЕШКА: Файлът '{DATA_PATH}' не е намерен. Моля, уверете се, че пътят е правилен.")
    full_dataset = pd.DataFrame()
    predictions_df = pd.DataFrame()
    countries = ["All"]
    divisions = ["All"]

# Дефиниране на променливите, които ще се използват в интерфейса
selected_country = "All"
selected_division = "All"
selected_date = None

# ==============================================================================
# Стъпка 5: Дефиниране на функции, които управляват логиката
# ==============================================================================

def filter_data(state: State):
    """Филтрира данните на база избраните филтри."""
    notify(state, "i", "Filtering data...")
    
    filtered_df = state.full_dataset.copy()
    
    if state.selected_country != "All":
        filtered_df = filtered_df[filtered_df['Country'] == state.selected_country]
        state.divisions = ["All"] + sorted(filtered_df['Division'].unique().tolist())
    else:
        state.divisions = ["All"]
        state.selected_division = "All"

    if state.selected_division != "All":
        filtered_df = filtered_df[filtered_df['Division'] == state.selected_division]
        
    if state.selected_date:
        selected_date_str = pd.to_datetime(state.selected_date).strftime('%Y-%m-%d')
        filtered_df = filtered_df[filtered_df['Date'] == selected_date_str]
    
    state.predictions_df = filtered_df
    notify(state, "s", "Data filtered successfully!")

def on_change(state: State, var_name: str, var_value):
    """Извиква филтриращата функция при промяна на филтър."""
    if var_name in ["selected_country", "selected_division", "selected_date"]:
        if var_name == "selected_country" and var_value != "All":
            state.selected_division = "All"
        filter_data(state)

# ==============================================================================
# Стъпка 6: Дефиниране на потребителския интерфейс (GUI)
# ==============================================================================

# Свойства на таблицата, за да оцветим вероятностите
# Колкото по-висока е вероятността, толкова по-наситен ще е цветът
table_properties = {
    # Стил за колоната с резултат
    "style[Result]": lambda val: {"color": "#28a745" if val == 'Home' else "#ffc107" if val == 'Draw' else "#dc3545" if val == 'Away' else ""},
    # Стил за вероятностите 1X2
    "style[Prob 1]": lambda val: {"background-color": f"rgba(0, 123, 255, {val})"} if isinstance(val, (int, float)) and val > 0.1 else {},
    "style[Prob X]": lambda val: {"background-color": f"rgba(0, 123, 255, {val})"} if isinstance(val, (int, float)) and val > 0.1 else {},
    "style[Prob 2]": lambda val: {"background-color": f"rgba(0, 123, 255, {val})"} if isinstance(val, (int, float)) and val > 0.1 else {},
    # Стил за вероятностите U/O
    "style[Prob U2.5]": lambda val: {"background-color": f"rgba(255, 193, 7, {val})"} if isinstance(val, (int, float)) and val > 0.1 else {},
    "style[Prob O2.5]": lambda val: {"background-color": f"rgba(255, 193, 7, {val})"} if isinstance(val, (int, float)) and val > 0.1 else {},
}

page_md = """
<|toggle|theme|>
<|part|class_name=container|
<|layout|columns=300px 1fr|
<|part|class_name=sidebar|
# <|toggle|theme|><|part|class_name=h1|**Predictions Dashboard**|>

### Filters

**Select Country:**\n
<|{selected_country}|selector|lov={countries}|dropdown=True|>

**Select Division:**\n
<|{selected_division}|selector|lov={divisions}|dropdown=True|>

**Select Date:**\n
<|{selected_date}|date|>
<|Reset Date|button|on_action=lambda s: s.assign("selected_date", None)|>

|>

<|part|
## **Match Predictions**
<br/>
<|{predictions_df}|table|page_size=20|width=100%|properties={table_properties}|>
|>
|>
|>
"""

# Създаваме GUI обекта и добавяме CSS стиловете
gui = Gui(page=page_md)

# CSS за дизайн "Професионално Синьо"
gui.add_style("h1 { padding: 10px; }")
gui.add_style(".container { background-color: #f8f9fa; padding: 20px; border-radius: 10px; }")
gui.add_style(".sidebar { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); }")

# ==============================================================================
# Стъпка 7: Стартиране на приложението
# ==============================================================================
# В Colab, кликнете на линка, за да отворите приложението.
# За Render, тази част ще бъде изпълнена от Gunicorn.
if __name__ == '__main__':
    gui.run(run_in_thread=True, use_reloader=False, title="Football Predictor")
