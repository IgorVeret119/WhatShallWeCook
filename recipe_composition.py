"""Keep source quantities and confirmed per-serving gram weights distinct."""
import json
import math
import re
from fractions import Fraction

def normalize(value):
    return ' '.join(re.findall(r'[^\W_]+',str(value).casefold().replace('ё','е')))

def numeric_quantity(value):
    text=re.sub(r'(?<=\d)([½¼¾])',r' \1',str(value or '').strip())
    text=text.replace('½','1/2').replace('¼','1/4').replace('¾','3/4')
    match=re.fullmatch(r'((?:\d+\s+)?\d+/\d+|\d+(?:\.\d+)?|\.\d+)\s*(.*)',text)
    if not match:return None,''
    if re.match(r'[-–—/\d]',match[2].strip()):return None,''
    try:
        amount=float(sum(Fraction(part) for part in match[1].split()))
        return (amount,match[2].strip()) if math.isfinite(amount) else (None,'')
    except (ValueError,ZeroDivisionError):return None,''

def match_food(name,foods):
    text=normalize(name)
    for key,food in foods.items():
        if text in {normalize(alias) for alias in food.get('aliases',[])}:
            return key
    return None

def composition(recipe,params,foods,excluded):
    names=recipe.get('ingredients',[])
    originals=recipe.get('ingredients_original',names)
    quantities=recipe.get('quantities',[])
    aligned=len(quantities)==len(names)
    servings=recipe.get('servings')
    per_serving=isinstance(servings,(int,float)) and math.isfinite(servings) and servings>0
    raw=params.get('ingredient_weights','[]')
    try:entries=json.loads(raw) if isinstance(raw,str) else raw
    except (ValueError,TypeError):raise ValueError('Некорректные массы ингредиентов.')
    if not isinstance(entries,list) or len(entries)>40:raise ValueError('Некорректные массы ингредиентов.')
    weights={}
    for entry in entries:
        if not isinstance(entry,dict):raise ValueError('Некорректные массы ингредиентов.')
        index=entry.get('index')
        if type(index) is not int or not 0<=index<len(names) or index in weights:
            raise ValueError('Некорректный номер ингредиента.')
        try:grams=float(entry['grams'])
        except (KeyError,ValueError,TypeError):raise ValueError('Укажите массу ингредиента в граммах.')
        if not math.isfinite(grams) or not 0<grams<=10000:raise ValueError('Масса ингредиента должна быть от 0 до 10000 г.')
        key=entry.get('food_id')
        if key is not None and (not isinstance(key,str) or key not in foods):raise ValueError('Неизвестный продукт для расчёта.')
        if key and excluded(foods[key],params.get('exclude','')):
            raise ValueError('Ингредиент находится в стоп-листе.')
        weights[index]=(grams,key)
    result=[]
    for index,name in enumerate(names):
        original=originals[index] if index<len(originals) else name
        key=match_food(original,foods)
        amount,unit=numeric_quantity(quantities[index]) if aligned else (None,'')
        source_quantity=amount/servings if amount is not None and per_serving else None
        grams=None
        if source_quantity is not None and normalize(unit) in ('g','gram','grams','г','грамм','граммов','kg','кг'):
            grams=source_quantity*(1000 if normalize(unit) in ('kg','кг') else 1)
        if index in weights:grams,key=weights[index]
        if key and excluded(foods[key],params.get('exclude','')):key=None
        result.append(dict(index=index,name=name,original_name=original,food_id=key,baseline_grams=grams,
                           source_quantity=source_quantity,source_unit=unit,quantity_aligned=aligned,
                           adjustable=bool(grams and key)))
    if sum(row['adjustable'] for row in result)>16:raise ValueError('Можно менять пропорции до 16 ингредиентов.')
    return result
