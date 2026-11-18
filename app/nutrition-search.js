// Soft targets rank every eligible recipe; they never add hard nutrition bounds.
let nutritionSearchTimer;
function syncNutritionTargets(){
 const enabled=document.querySelector('#nutrition-enabled').checked;
 document.querySelector('#nutrition-targets').classList.toggle('targets-disabled',!enabled);
 for(const input of document.querySelectorAll('#nutrition-targets input'))input.disabled=!enabled;
 const option=document.querySelector('#sort option[value="nutrition"]');option.disabled=!enabled;
 if(!enabled&&document.querySelector('#sort').value==='nutrition')document.querySelector('#sort').value='relevance';
 for(const input of document.querySelectorAll('[data-target-slider]')){
  const value=document.querySelector('[name="target_'+input.dataset.targetSlider+'"]');input.value=value.value;
 }
 updateTargetEnergy();
}
function updateTargetEnergy(){
 const value=key=>Number(document.querySelector('[name="target_'+key+'"]').value)||0;
 const energy=[value('protein')*4,value('fat')*9,value('carbs')*4],total=energy.reduce((a,b)=>a+b,0);
 const shares=energy.map(n=>total?n/total*100:0),rounded=shares.map(Math.floor);
 const remainder=100-rounded.reduce((a,b)=>a+b,0);
 const priority=[0,1,2].sort((a,b)=>(shares[b]-rounded[b])-(shares[a]-rounded[a]));
 if(total)for(let i=0;i<remainder;i++)rounded[priority[i]]++;
 document.querySelector('#target-energy').textContent=total?t('Доли энергии Б/Ж/У: ')+rounded.map(n=>n+'%').join(' / '):t('Задайте цели ползунками или числами.');
}
function queueNutritionSearch(){
 clearTimeout(nutritionSearchTimer);
 document.querySelector('#sort').value='nutrition';
 // Cancel the previous response immediately so it cannot paint stale results.
 if(typeof controller!=='undefined'&&controller)controller.abort();
 nutritionSearchTimer=setTimeout(()=>{if(document.querySelector('#filters').reportValidity()){page=1;load();}},400);
}
for(const slider of document.querySelectorAll('[data-target-slider]')){
 const number=document.querySelector('[name="target_'+slider.dataset.targetSlider+'"]');
 slider.addEventListener('input',()=>{number.value=slider.value;updateTargetEnergy();queueNutritionSearch();});
 number.addEventListener('input',()=>{slider.value=number.value;updateTargetEnergy();queueNutritionSearch();});
}
document.querySelector('#nutrition-enabled').addEventListener('change',()=>{
 syncNutritionTargets();if(document.querySelector('#nutrition-enabled').checked)document.querySelector('#sort').value='nutrition';
 clearTimeout(nutritionSearchTimer);page=1;load();
});
syncNutritionTargets();
