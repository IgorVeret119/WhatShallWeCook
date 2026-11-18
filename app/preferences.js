// Ingredient lists belong to the persistent anonymous profile issued by the server.
let productPreferences={liked_products:[],excluded_products:[]},preferencesLoaded=false,editingProductList='liked_products',productDraft=[],savingProducts=false,productEditorGeneration=0;
function getExcludedProducts(){return productPreferences.excluded_products.slice();}
function syncProductButtons(){
 for(const [kind,id,label] of [['liked_products','liked-products',t('Любимые продукты')],['excluded_products','excluded-products',t('Исключённые продукты')]]){
  const button=document.querySelector('#'+id),count=productPreferences[kind].length;
  button.querySelector('.product-count').textContent=String(count);button.classList.toggle('has-products',count>0);button.setAttribute('aria-label',label+' ('+count+')');button.title=label;
 }
}
async function loadProductPreferences(){
 const response=await fetch('/api/preferences');const data=await response.json();if(!response.ok)throw Error(uiError(data.error)||t('Не удалось загрузить списки продуктов.'));
 if(!Array.isArray(data.liked_products)||!Array.isArray(data.excluded_products))throw Error(t('Некорректный ответ сервера.'));
 productPreferences=data;preferencesLoaded=true;syncProductButtons();return data;
}
const productPreferencesReady=loadProductPreferences().catch(()=>{preferencesLoaded=false;syncProductButtons();});
function renderProductDraft(){
 const list=document.querySelector('#product-list');list.replaceChildren();
 for(let i=0;i<productDraft.length;i++){
  const item=document.createElement('li'),name=document.createElement('span'),remove=document.createElement('button');name.textContent=productDraft[i];remove.type='button';remove.textContent='×';remove.setAttribute('aria-label',t('Убрать ')+productDraft[i]+t(' из списка'));remove.onclick=()=>{productDraft.splice(i,1);renderProductDraft();};item.append(name,remove);list.append(item);
 }
 document.querySelector('#product-empty').hidden=productDraft.length>0;document.querySelector('#product-list-size').textContent=productDraft.length+' / 20';
}
async function openProductPreferences(kind){
 if(savingProducts)return;
 editingProductList=kind;const generation=++productEditorGeneration,dialog=document.querySelector('#product-preferences');
 document.querySelector('#product-title').textContent=kind==='liked_products'?t('Любимые продукты'):t('Исключённые продукты');
 document.querySelector('#product-description').textContent=kind==='liked_products'?t('Рецепты с этими продуктами будут выше при сортировке «По совпадению». Не обязательно, чтобы в блюде были все любимые продукты.'):t('Эти продукты будут исключаться при поиске рецептов и подборе добавок к блюду.');
 document.querySelector('#product-editor').hidden=true;document.querySelector('#preferences-retry').hidden=true;
 document.querySelector('#product-status').textContent=t('Загружаем список…');if(!dialog.open)dialog.showModal();
 try{await productPreferencesReady;await loadProductPreferences();
  if(!dialog.open||generation!==productEditorGeneration)return;
  productDraft=productPreferences[kind].slice();document.querySelector('#product-name').value='';renderProductDraft();document.querySelector('#product-status').textContent='';document.querySelector('#product-editor').hidden=false;document.querySelector('#product-name').focus();
 }catch(error){if(dialog.open&&generation===productEditorGeneration){document.querySelector('#product-status').textContent=error.message;document.querySelector('#preferences-retry').hidden=false;}}
}
document.querySelector('#liked-products').onclick=()=>openProductPreferences('liked_products');
document.querySelector('#excluded-products').onclick=()=>openProductPreferences('excluded_products');
document.querySelector('#preferences-retry').onclick=()=>openProductPreferences(editingProductList);
document.querySelector('#product-add-form').onsubmit=event=>{
 event.preventDefault();if(savingProducts)return;const input=document.querySelector('#product-name'),names=input.value.split(/[,\n]+/).map(value=>value.trim().replace(/\s+/g,' ')).filter(Boolean),status=document.querySelector('#product-status');
 if(!names.length){input.focus();return;}
 if(names.some(value=>value.length>80||!/[\p{L}]/u.test(value))){status.textContent=t('Укажите название продукта длиной до 80 символов.');return;}
 const draft=productDraft.slice();for(const name of names)if(!draft.some(old=>old.toLocaleLowerCase().replaceAll('ё','е')===name.toLocaleLowerCase().replaceAll('ё','е')))draft.push(name);
 if(draft.length>20){status.textContent=t('В одном списке можно сохранить до 20 продуктов.');return;}
 productDraft=draft;renderProductDraft();input.value='';status.textContent='';input.focus();
};
document.querySelector('#product-save').onclick=async()=>{
 if(savingProducts)return;savingProducts=true;
 const dialog=document.querySelector('#product-preferences'),status=document.querySelector('#product-status'),controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
 for(const button of dialog.querySelectorAll('button'))button.disabled=true;document.querySelector('#product-name').disabled=true;dialog.setAttribute('aria-busy','true');status.textContent=t('Сохраняем…');
 try{const response=await fetch('/api/preferences',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({[editingProductList]:productDraft}),signal:controller.signal});const data=await response.json();if(!response.ok)throw Error(uiError(data.error)||t('Не удалось сохранить список.'));
  productPreferences=data;preferencesLoaded=true;syncProductButtons();dialog.close();favoriteNotice(t('Список продуктов сохранён'));page=1;load();
 }catch(error){status.textContent=error.name==='AbortError'?t('Сервер долго не отвечает. Попробуйте сохранить ещё раз.'):uiError(error.message);}
 finally{clearTimeout(timeout);savingProducts=false;dialog.removeAttribute('aria-busy');document.querySelector('#product-name').disabled=false;for(const button of dialog.querySelectorAll('button'))button.disabled=false;}
};
document.querySelector('#product-close').onclick=document.querySelector('#product-cancel').onclick=()=>{if(!savingProducts)document.querySelector('#product-preferences').close();};
document.querySelector('#product-preferences').addEventListener('cancel',event=>{if(savingProducts)event.preventDefault();});
document.querySelector('#product-preferences').addEventListener('close',()=>{productEditorGeneration++;});
syncProductButtons();
