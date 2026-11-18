// UI messages are separate from recipe data and user-entered ingredient names.
let uiLanguage='ru';
try{if(localStorage.getItem('pet-project-language')==='en')uiLanguage='en';}catch(error){}
const englishMessages={
 'Поиск рецептов':'Recipe search',
 'Что приготовим?':'What shall we cook?',
 'Русский':'Russian', 'Язык рецептов':'Language', 'Предпочтения продуктов':'Ingredient preferences',
 'Любимые продукты':'Favorite ingredients','Исключённые продукты':'Excluded ingredients',
 'Любимые продукты (0)':'Favorite ingredients (0)','Исключённые продукты (0)':'Excluded ingredients (0)',
 'Разделы рецептов':'Recipe sections','Все рецепты':'All recipes','Любимые блюда':'Favorite recipes',
 'Название или ключевые слова':'Name or keywords',
 'Например: chicken soup или курица суп':'For example: chicken soup',
 'Ближе к вашему КБЖУ':'Match your nutrition goals','Подбирать по КБЖУ':'Match nutrition goals',
 'Калории':'Calories','Белки':'Protein','Жиры':'Fat','Углеводы':'Carbs','Белок':'Protein',
 'ккал':'kcal','г':'g','Б, г':'P, g','Ж, г':'F, g','У, г':'C, g',
 'Калории, ккал':'Calories, kcal','Белки, г':'Protein, g','Жиры, г':'Fat, g','Углеводы, г':'Carbs, g',
 'Цель: калории':'Calorie target','Цель: белки':'Protein target','Цель: жиры':'Fat target','Цель: углеводы':'Carb target',
 'Калории: ползунок цели':'Calorie target slider','Белки: ползунок цели':'Protein target slider',
 'Жиры: ползунок цели':'Fat target slider','Углеводы: ползунок цели':'Carb target slider',
 'Цель на одну порцию. Двигайте ползунки — ближайшие рецепты будут выше. Это ориентир, а не строгий фильтр.':'Targets per serving. Move the sliders to rank the closest recipes first. These are guides, not strict filters.',
 'Найти рецепты':'Find recipes','Сбросить':'Reset','Сортировка':'Sort by','Ближе к КБЖУ':'Closest nutrition match',
 'По совпадению':'Relevance','По названию':'Name','Меньше калорий':'Lowest calories','Больше белка':'Highest protein',
 'Загрузка…':'Loading…','Страницы':'Pages','← Назад':'← Previous','Далее →':'Next →',
 'Продукты':'Ingredients','Закрыть список':'Close list','Попробовать ещё раз':'Try again',
 'Добавить продукт':'Add ingredient','Например, брокколи':'For example, broccoli','Добавить':'Add',
 'Несколько продуктов можно ввести через запятую.':'Separate multiple ingredients with commas.',
 'Список пока пуст.':'This list is empty.',
 'Списки сохраняются для вашего профиля в этом браузере. Изменения применяются кнопкой «Сохранить».':'Lists are saved to your profile in this browser. Select Save to apply your changes.',
 'Отмена':'Cancel','Сохранить':'Save',
 'Рецепты с этими продуктами будут выше при сортировке «По совпадению». Не обязательно, чтобы в блюде были все любимые продукты.':'Recipes with these ingredients rank higher when sorted by Relevance. A recipe does not need to contain all your favorites.',
 'Эти продукты будут исключаться при поиске рецептов и подборе добавок к блюду.':'These ingredients are excluded from recipe search and suggested meal additions.',
 'Не удалось загрузить списки продуктов.':'Could not load ingredient lists.',
 'Некорректный ответ сервера.':'The server returned an invalid response.',
 'Загружаем список…':'Loading list…','Убрать ':'Remove ',' из списка':' from the list',
 'Укажите название продукта длиной до 80 символов.':'Enter an ingredient name with up to 80 characters.',
 'В одном списке можно сохранить до 20 продуктов.':'You can save up to 20 ingredients per list.',
 'Сохраняем…':'Saving…','Не удалось сохранить список.':'Could not save the list.',
 'Список продуктов сохранён':'Ingredient list saved',
 'Сервер долго не отвечает. Попробуйте сохранить ещё раз.':'The server is taking too long. Try saving again.',
 'Убрать из любимых: ':'Remove from favorites: ','Добавить в любимые: ':'Add to favorites: ',
 'Не удалось сохранить любимое блюдо.':'Could not save this favorite.',
 'Не удалось сохранить любимое блюдо. Проверьте соединение с сервером.':'Could not save this favorite. Check your connection to the server.',
 'Блюдо добавлено в любимые':'Recipe added to favorites','Блюдо удалено из любимых':'Recipe removed from favorites',
 'Сбросить фильтры':'Reset filters','Найти блюда':'Find recipes',
 'Нет любимых блюд по этим фильтрам':'No favorites match these filters','Пока нет любимых блюд':'No favorites yet',
 'Проверьте фильтры поиска и список исключённых продуктов, чтобы увидеть сохранённые рецепты.':'Check your search filters and excluded ingredients to see your saved recipes.',
 'Нажмите на сердечко в карточке — блюдо появится здесь.':'Select the heart on a recipe card to save it here.',
 'Настроить КБЖУ':'Adjust nutrition','Загружаем настройки…':'Loading meal settings…',
 'Закрыть настройку':'Close meal settings','Выбрать и настроить КБЖУ':'Select and adjust nutrition',
 'Для этого блюда нет полных данных КБЖУ. Пересчёт недоступен.':'This recipe has incomplete nutrition data. Meal adjustment is unavailable.',
 'Размер порции меняет все показатели вместе. Измените цели КБЖУ, чтобы подобрать порцию и добавки. Готовые добавки можно подать отдельно.':'Portion size scales all nutrients together. Adjust your targets to find a portion and additions. Additions can be served on the side.',
 'Размер порции':'Portion size','1 × исходная порция':'1 × original serving',' × исходная порция':' × original serving',
 ' × исходная порция.':' × original serving.','Цель: ':'Target: ','Точное значение: ':'Exact value: ',
 'Укажите корректные числовые цели.':'Enter valid numeric targets.','Цели для тарелки':'Meal targets',
 'Какие продукты можно добавить':'Available additions','Добавка: ':'Addition: ','Без добавки':'No addition',
 ' — исключён фильтром':' — excluded by your preferences',
 'Масса добавок — в граммах съедобного продукта. Показатели справочные: состав конкретного продукта может отличаться.':'Addition weights are in grams of edible food. Nutrition values are estimates and may vary by product.',
 'Вернуть исходную порцию':'Restore original serving','Считаем…':'Calculating…',
 'Расчёт близок ко всем заданным целям.':'This estimate is close to all your targets.',
 'Не все цели достижимы вместе. Показан ближайший из рассчитанных вариантов — сравните значения ниже.':'Not all targets can be reached together. The closest calculated option is shown; compare the values below.',
 'Показатель':'Nutrient','На 1 порцию':'Per serving','Цель':'Target','Получится':'Result',' к цели':' from target',
 'Основное блюдо: ':'Main dish: ','Добавить: ':'Add: ',' г.':' g.',
 'Добавки не требуются или не выбраны.':'No additions are needed or selected.',
 'Доли энергии из БЖУ: Б ':'Energy from macros: P ','% · Ж ':'% · F ','% · У ':'% · C ',
 'Расчёт ориентировочный. Калории берутся из базы отдельно от БЖУ; пересчёт по 4/9/4 может дать другое значение.':'This is an estimate. Calories come from the dataset separately from macros; calculating them with 4/9/4 may give a different value.',
 'Доли энергии Б/Ж/У: ':'Energy share P/F/C: ','Задайте цели ползунками или числами.':'Set targets using the sliders or numbers.',
 'Фотография недоступна':'Photo unavailable','Ингредиенты':'Ingredients','Состав не указан':'Ingredients not provided',
 'На весь рецепт':'For the whole recipe',' · Порций: ':' · Servings: ','Приготовление':'Directions',
 'Шаги приготовления не указаны.':'Directions not provided.','Все шаги (':'All steps (','Свернуть':'Show less',
 'Иллюстрация блюда: ':'Dish illustration: ',' мин · ':' min · ','КБЖУ на порцию':'Nutrition per serving',
 'Отклонение от цели: ':'Deviation from target: ','КБЖУ указано не полностью':'Incomplete nutrition data',
 'Среднеквадратичное относительное отклонение КБЖУ. Меньше — ближе к вашей цели.':'Root mean square relative nutrition deviation. Lower is closer to your targets.',
 'Ошибка запроса':'Request failed','Ищем рецепты…':'Searching recipes…','Любимые блюда: ':'Favorite recipes: ',
 ' · Всего сохранено: ':' · Saved: ','Найдено: ':'Found: ',' · В базе: ':' · In database: ',
 'База рецептов пока пуста':'The recipe database is empty',
 'Загрузите рецепты командой в папке проекта:':'Load recipes by running this command in the project folder:',
 'Подходящих рецептов нет':'No matching recipes',
 'Измените запрос, ограничения КБЖУ или список исключённых продуктов.':'Change your search, nutrition settings or excluded ingredients.',
 'Не удалось выполнить поиск':'Search failed',
 'Куриная грудка, готовая':'Cooked chicken breast','Греческий йогурт без добавок, 0%':'Plain Greek yogurt, 0% fat',
 'Рис белый, варёный':'Cooked white rice','Банан без кожуры':'Peeled banana','Оливковое масло':'Olive oil','Миндаль':'Almonds',
 'Failed to fetch':'Could not connect to the server. Please try again.',
 'Порция':'Portion',
 'Не удалось сохранить продукты. Попробуйте ещё раз.':'Could not save ingredients. Please try again.',
 'Один продукт не может быть одновременно любимым и исключённым.':'An ingredient cannot be both a favorite and excluded.',
 'Цели КБЖУ должны быть числами от 0 до 1000000.':'Nutrition targets must be numbers between 0 and 1000000.',
 'Ошибка базы данных. Подробности в консоли сервера.':'Database error. See the server console for details.',
 'Некорректный профиль.':'Invalid browser profile.','Передайте список продуктов.':'Provide an ingredient list.',
 'Название продукта должно быть текстом.':'Ingredient names must be text.',
 'Укажите любимые или исключённые продукты.':'Provide favorite or excluded ingredients.',
 'Не больше 20 слов в запросе.':'Use up to 20 words in your search.',
 'Не больше 20 ингредиентов в поле.':'Use up to 20 ingredients per field.',
 'Укажите название ингредиента.':'Enter an ingredient name.',
 'Числовые фильтры должны быть конечными и неотрицательными.':'Numeric filters must be finite, non-negative numbers.',
 'Минимум не может быть больше максимума.':'The minimum cannot exceed the maximum.',
 'Некорректное время приготовления.':'Invalid cooking time.','Некорректная страница.':'Invalid page.',
 'Не больше 20 любимых продуктов.':'Use up to 20 favorite ingredients.',
 'Слишком длинный запрос.':'The request is too long.','Рецепт не найден.':'Recipe not found.',
 'Страница не найдена.':'Page not found.','Недопустимый источник запроса.':'Invalid request origin.',
 'Не удалось сохранить любимое блюдо. Попробуйте ещё раз.':'Could not save this favorite. Please try again.',
 'Некорректный размер списка.':'Invalid list size.',
 'Неизвестный способ пересчёта.':'Unknown adjustment method.',
 'Выберите не более трёх разных продуктов из списка.':'Select up to three different foods from the list.',
 'Выберите по одному продукту из каждой группы.':'Select one food from each group.',
 'Уточнить массы и продукты':'Edit ingredient weights and foods',
 'Введите граммы каждого продукта в одной исходной порции и проверьте, сырой он или готовый. Пустые массы не угадываем.':'Enter grams per original serving and check whether each food is raw or cooked. Unknown weights are left blank.',
 'Разрешить новые ингредиенты':'Allow new ingredients',
 'Подобрать автоматически':'Choose automatically',
 ' г / 100 г':' g / 100 g',
 'Список без продуктов из стоп-листа. Варианты сгруппированы по основному нутриенту; количество указано на 100 г. Добавки готовятся или подаются отдельно.':'Excluded foods are removed. Options are grouped by their main nutrient, with amounts per 100 g. Prepare or serve additions separately.',
 'Масса, г':'Weight, g','Масса на порцию: ':'Weight per serving: ',
 'Только масштабировать по порции':'Scale with the portion only','Продукт для расчёта: ':'Nutrition reference food: ',
 'Состав вашей порции':'Ingredients in your serving',' г':' g',' (ед. рецепта)':' (recipe units)',
 ' исходного количества':' of the original amount','% к пропорции блюда':'% relative to the dish ratio',
 'Сейчас меняется порция целиком. Для отдельных пропорций уточните массы продуктов ниже.':'The whole portion is being scaled. Enter ingredient weights below to adjust individual proportions.',
 'Известные ингредиенты меняются в пределах ±20% относительно порции; остальные масштабируются вместе с ней.':'Ingredients with confirmed weights vary by up to ±20% relative to the portion; the rest scale together.',
 'В исходных данных количества не сопоставлены с ингредиентами. Показываем коэффициенты; граммы можно указать ниже.':'Source quantities cannot be matched reliably to ingredients. Scaling factors are shown; you can enter grams below.',
 'Текущего состава недостаточно для цели. Можно разрешить новые ингредиенты и выбрать подходящие ниже.':'The current ingredients cannot reach this target. Allow additions and choose suitable foods below.',
 'Предложить добавки':'Suggest additions',
 'Некорректные массы ингредиентов.':'Invalid ingredient weights.',
 'Некорректный номер ингредиента.':'Invalid ingredient index.',
 'Укажите массу ингредиента в граммах.':'Enter the ingredient weight in grams.',
 'Масса ингредиента должна быть от 0 до 10000 г.':'Ingredient weight must be greater than 0 and no more than 10000 g.',
 'Неизвестный продукт для расчёта.':'Unknown nutrition reference food.',
 'Ингредиент находится в стоп-листе.':'This ingredient is in your exclusion list.',
 'Можно менять пропорции до 16 ингредиентов.':'You can adjust up to 16 ingredients.',
 'Указанные массы превышают КБЖУ исходной порции. Проверьте граммы и выбранные продукты.':'The entered weights exceed the original serving nutrition. Check the grams and selected reference foods.'
};
function t(message){return uiLanguage==='en'?(englishMessages[message]??message):message;}
function uiError(message){
 const text=String(message||t('Ошибка запроса'));
 if(uiLanguage!=='en')return text;
 if(englishMessages[text])return englishMessages[text];
 const conflict=text.match(/^Продукт «(.+)» не может быть одновременно любимым и исключённым\.$/);
 if(conflict)return '“'+conflict[1]+'” cannot be both a favorite and excluded.';
 const excluded=text.match(/^Продукт «(.+)» исключён вашим фильтром\.$/);
 if(excluded)return '“'+t(excluded[1])+'” is excluded by your preferences.';
 const invalid=text.match(/^Некорректное значение: (.+)\.$/);
 if(invalid)return 'Invalid value: '+(invalid[1]==='порция'?'portion':invalid[1])+'.';
 const bounds=text.match(/^Значение (.+) вне допустимого диапазона\.$/);
 if(bounds)return 'The value for '+(bounds[1]==='порция'?'portion':bounds[1])+' is outside the allowed range.';
 if(/[А-Яа-яЁё]/.test(text))return 'Could not complete the request. Check your input and try again.';
 return text==='Failed to fetch'?englishMessages[text]:text;
}
// Remember the original static text once; never translate recipe or user data.
const staticTranslations=[];
const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
while(walker.nextNode()){
 const text=walker.currentNode;if(text.parentElement.closest('script,style'))continue;
 const original=text.textContent,trimmed=original.trim();
 if(englishMessages[trimmed])staticTranslations.push(()=>{text.textContent=uiLanguage==='en'?original.replace(trimmed,englishMessages[trimmed]):original;});
}
for(const element of document.querySelectorAll('[placeholder],[aria-label],[title]')){
 for(const attribute of ['placeholder','aria-label','title']){
  const original=element.getAttribute(attribute);if(original&&englishMessages[original])staticTranslations.push(()=>element.setAttribute(attribute,t(original)));
 }
}
function applyInterfaceLanguage(language){
 uiLanguage=language==='en'?'en':'ru';document.documentElement.lang=uiLanguage;document.title=t('Поиск рецептов');
 for(const update of staticTranslations)update();
 const notice=document.querySelector('#favorite-notice');if(notice)notice.hidden=true;
 document.querySelector('.hero-title img').src=uiLanguage==='en'?'/title-calligraphy-en.png':'/title-calligraphy.png';
}
applyInterfaceLanguage(uiLanguage);
