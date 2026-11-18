// Favorites are saved by the local server, not just in the current page.
let recipeView='all',favoriteCount=0,favoriteRevision=0,favoriteQueue=Promise.resolve(),favoritesRefreshTimer,noticeTimer;
const pendingFavoriteIds=new Set();
try{if(localStorage.getItem('pet-project-view')==='favorites')recipeView='favorites';}catch(error){}

function syncFavoriteNavigation(count=favoriteCount){
 favoriteCount=count;
 document.querySelector('#favorites-count').textContent=String(count);
 document.querySelector('#show-all').setAttribute('aria-pressed',String(recipeView==='all'));
 document.querySelector('#show-favorites').setAttribute('aria-pressed',String(recipeView==='favorites'));
}
function switchRecipeView(view){
 if(view===recipeView)return;
 recipeView=view;page=1;syncFavoriteNavigation();
 try{localStorage.setItem('pet-project-view',view);}catch(error){}
 load();
}
function favoriteNotice(message,isError=false){
 const notice=document.querySelector('#favorite-notice');clearTimeout(noticeTimer);
 notice.textContent=message;notice.classList.toggle('notice-error',isError);notice.hidden=false;
 noticeTimer=setTimeout(()=>{notice.hidden=true;},isError?5000:2500);
}
function updateFavoriteButton(button,saved){
 button.setAttribute('aria-pressed',String(saved));button.classList.toggle('is-favorite',saved);
 const label=(saved?t('Убрать из любимых: '):t('Добавить в любимые: '))+button.dataset.recipeName;
 button.setAttribute('aria-label',label);button.title=label;
 if(!saved){button.classList.remove('just-added');clearTimeout(button.favoriteAnimationTimer);}
}
function animateFavorite(button){
 clearTimeout(button.favoriteAnimationTimer);button.classList.remove('just-added');
 requestAnimationFrame(()=>{if(button.isConnected&&button.getAttribute('aria-pressed')==='true')button.classList.add('just-added');});
 button.favoriteAnimationTimer=setTimeout(()=>button.classList.remove('just-added'),700);
}
function createFavoriteButton(recipe){
 const button=document.createElement('button');button.type='button';button.className='favorite-button';
 button.dataset.favoriteId=String(recipe.id);button.dataset.recipeName=recipe.name;
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.classList.add('heart-icon');
 const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d','M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z');svg.append(path);button.append(svg);
 updateFavoriteButton(button,Boolean(recipe.is_favorite));
 button.disabled=pendingFavoriteIds.has(recipe.id);if(button.disabled)button.setAttribute('aria-busy','true');
 button.onclick=event=>{event.stopPropagation();toggleFavorite(recipe.id,button);};
 return button;
}
function toggleFavorite(id,button){
 if(pendingFavoriteIds.has(id))return;
 const saved=button.getAttribute('aria-pressed')!=='true';pendingFavoriteIds.add(id);button.disabled=true;button.setAttribute('aria-busy','true');
 favoriteQueue=favoriteQueue.catch(()=>{}).then(async()=>{
  const response=await fetch('/api/favorites/'+id,{method:saved?'POST':'DELETE',headers:{'Content-Type':'application/json'},body:saved?'{}':undefined});
  const result=await response.json();if(!response.ok)throw Error(uiError(result.error)||t('Не удалось сохранить любимое блюдо.'));
  favoriteRevision++;syncFavoriteNavigation(result.favorites_count);
  document.querySelectorAll('[data-favorite-id="'+id+'"]').forEach(current=>{updateFavoriteButton(current,result.is_favorite);if(result.is_favorite)animateFavorite(current);});
  favoriteNotice(result.is_favorite?t('Блюдо добавлено в любимые'):t('Блюдо удалено из любимых'));
  if(recipeView==='favorites'){
   if(!result.is_favorite){const card=button.closest('.card');if(card)card.classList.add('favorite-removing');}
   clearTimeout(favoritesRefreshTimer);favoritesRefreshTimer=setTimeout(()=>{if(recipeView==='favorites')load();},200);
  }
 }).catch(error=>{favoriteNotice(error.message==='Failed to fetch'?t('Не удалось сохранить любимое блюдо. Проверьте соединение с сервером.'):uiError(error.message),true);})
 .finally(()=>{pendingFavoriteIds.delete(id);document.querySelectorAll('[data-favorite-id="'+id+'"]').forEach(current=>{current.disabled=false;current.removeAttribute('aria-busy');});});
}
function favoritesEmptyState(){
 const empty=node('div',null,'empty'),action=node('button',favoriteCount?t('Сбросить фильтры'):t('Найти блюда'),'empty-action');action.type='button';
 empty.append(node('h2',favoriteCount?t('Нет любимых блюд по этим фильтрам'):t('Пока нет любимых блюд')),
              node('p',favoriteCount?t('Проверьте фильтры поиска и список исключённых продуктов, чтобы увидеть сохранённые рецепты.'):t('Нажмите на сердечко в карточке — блюдо появится здесь.')));
 action.onclick=()=>{if(favoriteCount)form.reset();else switchRecipeView('all');};empty.append(action);return empty;
}
document.querySelector('#show-all').onclick=()=>switchRecipeView('all');
document.querySelector('#show-favorites').onclick=()=>switchRecipeView('favorites');
syncFavoriteNavigation();
