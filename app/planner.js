// Keep recipe units distinct from confirmed grams; do not infer ingredient weights.
let activeRecipePlanner=null;
const formatPortion=value=>new Intl.NumberFormat(uiLanguage,{maximumFractionDigits:2}).format(value);
const formatIngredientWeight=value=>new Intl.NumberFormat(uiLanguage,{maximumFractionDigits:value>0&&value<1?3:1}).format(value);
function closeRecipePlanner(){if(activeRecipePlanner){activeRecipePlanner.close();activeRecipePlanner=null;}}
function foodLabel(food){return uiLanguage==='en'?(food.name_en||t(food.name)):food.name;}
async function chooseRecipe(recipe,card,button){
 if(activeRecipePlanner&&activeRecipePlanner.card===card){closeRecipePlanner();return;}
 closeRecipePlanner();
 const panel=node('section',null,'planner');panel.id='planner-'+recipe.id;
 const status=node('p',t('Загружаем настройки…'),'planner-status');status.setAttribute('role','status');
 panel.append(node('h3',t('Настроить КБЖУ')),status);card.append(panel);card.classList.add('selected');button.textContent=t('Закрыть настройку');button.setAttribute('aria-expanded','true');button.setAttribute('aria-controls',panel.id);
 let disposed=false,job=new AbortController(),timer,editorReady=false;
 activeRecipePlanner={card,close:()=>{disposed=true;clearTimeout(timer);job.abort();panel.remove();card.classList.remove('selected');button.textContent=t('Выбрать и настроить КБЖУ');button.setAttribute('aria-expanded','false');}};
 const keys=['calories','protein','fat','carbs'],labels={calories:t('Калории, ккал'),protein:t('Белки, г'),fat:t('Жиры, г'),carbs:t('Углеводы, г')};
 if(keys.some(key=>recipe[key]==null||!Number.isFinite(Number(recipe[key])))){status.textContent=t('Для этого блюда нет полных данных КБЖУ. Пересчёт недоступен.');return;}
 try{
 const catalogData=await api('/api/nutrition/foods',job.signal);if(disposed)return;
 const foods=catalogData.foods.filter(food=>!food.excluded);
 for(const food of foods)if(food.name_en)englishMessages[food.name]=food.name_en;
 const portionLabel=node('label',null,'portion-control'),portionValue=node('output',t('1 × исходная порция')),portion=node('input');
 portion.type='range';portion.min='.25';portion.max='3';portion.step='.05';portion.value='1';portion.setAttribute('aria-label',t('Размер порции'));portion.dataset.portion='true';portionLabel.append(node('span',t('Размер порции')),portionValue,portion);panel.append(portionLabel);
 const targetGrid=node('div',null,'target-grid'),targets={};
 for(const key of keys){
  const label=node('label',labels[key]),controls=node('div',null,'target-control'),range=node('input'),number=node('input');range.type='range';number.type='number';
  const max=Math.max({calories:1800,protein:150,fat:120,carbs:250}[key],Math.ceil(Number(recipe[key])*3/100)*100);
  for(const input of [range,number]){input.min='0';input.max=String(max);input.step='.1';input.value=String(recipe[key]);input.setAttribute('aria-label',(input===range?t('Цель: '):t('Точное значение: '))+labels[key]);}
  number.dataset.mealTarget=key;range.dataset.mealSlider=key;
  range.oninput=()=>{number.value=range.value;schedule('fit');};number.oninput=()=>{range.value=number.value;schedule('fit');};
  controls.append(range,number);label.append(controls);targetGrid.append(label);targets[key]={range,number};
 }
 panel.append(node('h4',t('Цели для тарелки')),targetGrid);
 const result=node('div',null,'planner-result');result.setAttribute('aria-live','polite');panel.append(result);
 const weightEditor=node('details',null,'weight-editor');weightEditor.append(node('summary',t('Уточнить массы и продукты')));
 weightEditor.append(node('p',t('Введите граммы каждого продукта в одной исходной порции и проверьте, сырой он или готовый. Пустые массы не угадываем.'),'hint'));
 const editorRows=node('div',null,'weight-editor-rows'),weights=new Map();weightEditor.append(editorRows);panel.append(weightEditor);
 const additionsPanel=node('section',null,'additions-panel'),allow=node('input');allow.type='checkbox';allow.id='allow-additions-'+recipe.id;
 const allowLabel=node('label',null,'allow-additions');allowLabel.append(allow,document.createTextNode(t('Разрешить новые ингредиенты')));additionsPanel.append(allowLabel);
 const products=node('div',null,'product-grid'),selectors={};
 for(const [group,labelText] of [['protein',t('Белок')],['carbs',t('Углеводы')],['fat',t('Жиры')]]){
  const label=node('label',labelText),select=node('select');select.dataset.additionGroup=group;select.setAttribute('aria-label',t('Добавка: ')+labelText);
  const auto=node('option',t('Подобрать автоматически'));auto.value='_auto';select.append(auto);const none=node('option',t('Без добавки'));none.value='';select.append(none);
  for(const food of foods.filter(food=>food.group===group&&food.addition)){
   const option=node('option',foodLabel(food)+' — '+fmt(food[group])+t(' г / 100 г'));option.value=food.id;select.append(option);
  }
  select.disabled=true;select.onchange=()=>schedule('fit');selectors[group]=select;label.append(select);products.append(label);
 }
 additionsPanel.append(products,node('p',t('Список без продуктов из стоп-листа. Варианты сгруппированы по основному нутриенту; количество указано на 100 г. Добавки готовятся или подаются отдельно.'),'hint'));panel.append(additionsPanel);
 allow.onchange=()=>{for(const select of Object.values(selectors))select.disabled=!allow.checked;schedule('fit',0);};
 const reset=node('button',t('Вернуть исходную порцию'),'planner-reset');reset.type='button';reset.onclick=()=>{portion.value='1';allow.checked=false;for(const select of Object.values(selectors))select.disabled=true;for(const key of keys)targets[key].range.value=targets[key].number.value=String(recipe[key]);schedule('portion',0);};panel.append(reset);
 portion.oninput=()=>{portionValue.textContent=formatPortion(Number(portion.value))+t(' × исходная порция');for(const key of keys)targets[key].range.value=targets[key].number.value=String(Math.round(recipe[key]*Number(portion.value)*10)/10);schedule('portion');};
 function schedule(mode,delay=240){
  clearTimeout(timer);job.abort();
  const invalid=[...Object.values(targets).map(pair=>pair.number),...Array.from(weights.values(),entry=>entry.input)].find(input=>input.value!==''&&!input.checkValidity());
  if(invalid||Object.values(targets).some(pair=>pair.number.value==='')){status.textContent=t('Укажите корректные числовые цели.');return;}
  timer=setTimeout(()=>calculate(mode),delay);
 }
 function buildEditor(ingredients){
  if(editorReady)return;editorReady=true;
  for(const row of ingredients){
   const line=node('div',null,'weight-editor-row'),label=node('label',row.name),input=node('input'),profile=node('select');
   input.type='number';input.min='.1';input.max='10000';input.step='.1';input.placeholder=t('Масса, г');input.dataset.ingredientIndex=row.index;input.setAttribute('aria-label',t('Масса на порцию: ')+row.name);
   if(row.baseline_grams!=null)input.value=String(row.baseline_grams);
   const none=node('option',t('Только масштабировать по порции'));none.value='';profile.append(none);
   for(const food of foods){const option=node('option',foodLabel(food));option.value=food.id;profile.append(option);}
   profile.value=row.food_id||'';profile.setAttribute('aria-label',t('Продукт для расчёта: ')+row.name);input.oninput=profile.onchange=()=>schedule('fit');
   weights.set(row.index,{input,profile});label.append(input);line.append(label,profile);editorRows.append(line);
  }
 }
 function render(plan,mode){
  result.replaceChildren();
  const macrosRow=node('div',null,'meal-macros');macrosRow.setAttribute('aria-label',t('Получится'));
  for(const key of keys){const cell=node('div',null,'meal-macro');cell.append(node('span',labels[key]),node('strong',fmt(plan.actual[key])));
   const delta=plan.difference[key];cell.append(node('small',t('Цель: ')+fmt(plan.targets[key])+(mode==='fit'?' · '+(delta>0?'+':'')+fmt(delta):'')));macrosRow.append(cell);
  }
  result.append(macrosRow,node('h4',t('Состав вашей порции')));
  const list=node('ul',null,'meal-ingredients');
  for(const row of plan.ingredients){
   const item=node('li'),amount=node('span',null,'ingredient-amount'),factor=formatPortion(row.factor);item.append(node('span',row.name));
   if(row.grams!=null)amount.textContent=formatIngredientWeight(row.baseline_grams)+' → '+formatIngredientWeight(row.grams)+t(' г');
   else if(row.quantity!=null)amount.textContent=fmt(row.source_quantity)+' → '+fmt(row.quantity)+(row.source_unit?' '+row.source_unit:'')+t(' (ед. рецепта)');
   else amount.textContent='× '+factor+t(' исходного количества');
   if(row.adjustable&&Math.abs(row.factor-plan.portion)>.005){item.classList.add('ingredient-changed');amount.append(node('small',(row.factor>plan.portion?'+':'')+fmt((row.factor/plan.portion-1)*100)+t('% к пропорции блюда')));}
   item.append(amount);list.append(item);
  }
  for(const food of plan.additions){const item=node('li',null,'ingredient-added');item.append(node('span',t('Добавить: ')+foodLabel(food)),node('span',fmt(food.grams)+t(' г'),'ingredient-amount'));list.append(item);}
  result.append(list);
  if(!plan.adjustable_count)result.append(node('p',t('Сейчас меняется порция целиком. Для отдельных пропорций уточните массы продуктов ниже.'),'hint'));
  else result.append(node('p',t('Известные ингредиенты меняются в пределах ±20% относительно порции; остальные масштабируются вместе с ней.'),'hint'));
  if(!plan.quantities_aligned)result.append(node('p',t('В исходных данных количества не сопоставлены с ингредиентами. Показываем коэффициенты; граммы можно указать ниже.'),'hint'));
  if(plan.suggest_additions&&!allow.checked){
   const suggestion=node('div',null,'addition-suggestion');suggestion.append(node('p',t('Текущего состава недостаточно для цели. Можно разрешить новые ингредиенты и выбрать подходящие ниже.')));
   const accept=node('button',t('Предложить добавки'));accept.type='button';accept.onclick=()=>{allow.checked=true;allow.onchange();};suggestion.append(accept);result.append(suggestion);
  }
 }
 async function calculate(mode){
  if(disposed)return;job=new AbortController();const current=job;status.textContent=t('Считаем…');panel.setAttribute('aria-busy','true');
  const entries=[];for(const [index,entry] of weights)if(entry.input.value!=='')entries.push({index,grams:Number(entry.input.value),food_id:entry.profile.value||null});
  const params=new URLSearchParams({mode,portion:portion.value,lang:uiLanguage,allow_additions:allow.checked?'1':'0',
   foods:Object.values(selectors).map(select=>select.value).filter(value=>value&&value!=='_auto').join(','),
   auto_groups:Object.entries(selectors).filter(([,select])=>select.value==='_auto').map(([key])=>key).join(','),ingredient_weights:JSON.stringify(entries)});
  for(const key of keys)params.set(key,targets[key].number.value);
  try{
   const plan=await api('/api/recipes/'+recipe.id+'/balance?'+params,current.signal);if(disposed||job!==current)return;
   portion.value=String(plan.portion);portionValue.textContent=formatPortion(plan.portion)+t(' × исходная порция');
   status.textContent=plan.within_tolerance?t('Расчёт близок ко всем заданным целям.'):t('Не все цели достижимы вместе. Показан ближайший из рассчитанных вариантов — сравните значения ниже.');status.classList.toggle('approximate',!plan.within_tolerance);
   buildEditor(plan.ingredients);render(plan,mode);
  }catch(error){if(error.name!=='AbortError'&&!disposed&&job===current){status.textContent=uiError(error.message);status.classList.add('approximate');result.replaceChildren();}}
  finally{if(job===current)panel.setAttribute('aria-busy','false');}
 }
 calculate('portion');
 }catch(error){if(error.name!=='AbortError'&&!disposed)status.textContent=uiError(error.message);}
}
