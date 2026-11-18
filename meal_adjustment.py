"""Reference-based meal adjustment with conservative ingredient changes first."""
import itertools
import json
import math
import re
from pathlib import Path
from recipe_composition import composition,normalize

FIELDS=('calories','protein','fat','carbs')
FOODS=json.loads((Path(__file__).resolve().parent/'data'/'nutrition_foods.json').read_text(encoding='utf8'))

def finite(value,name,minimum=0,maximum=1_000_000):
    try:result=float(value)
    except (ValueError,TypeError):raise ValueError(f'Некорректное значение: {name}.')
    if not math.isfinite(result) or not minimum<=result<=maximum:raise ValueError(f'Значение {name} вне допустимого диапазона.')
    return result

def base_nutrition(recipe):
    if any(recipe.get(k) is None for k in FIELDS):
        raise ValueError('Для этого блюда нет полных данных КБЖУ. Пересчёт недоступен.')
    return {k:finite(recipe[k],k) for k in FIELDS}

def excluded_food(food,exclusions):
    from recipes import translate
    vocabulary=' '.join([food.get('tags',''),food.get('name',''),food.get('name_en',''),*food.get('aliases',[])])
    tags=set(normalize(vocabulary).split())
    translated_tags=set(translate(vocabulary).split())
    for term in exclusions.split(','):
        words=normalize(term).split();translated=translate(term).split()
        if (words and all(w in tags for w in words)) or (translated and all(w in translated_tags for w in translated)):
            return True
    return False

def catalog(exclusions=''):
    # Stop-listed foods are absent, including profiles used for original ingredients.
    return [dict(id=key,**{k:v for k,v in food.items() if k not in ('tags','aliases')},excluded=False)
            for key,food in FOODS.items() if not excluded_food(food,exclusions)]

def totals(base,portion,additions):
    return {k:base[k]*portion+sum(FOODS[i][k]*g/100 for i,g in additions) for k in FIELDS}

def reached(actual,targets):
    tolerance={'calories':max(15,targets['calories']*.03),'protein':max(1.5,targets['protein']*.05),
               'fat':max(1,targets['fat']*.05),'carbs':max(2,targets['carbs']*.05)}
    return all(abs(actual[k]-targets[k])<=tolerance[k] for k in FIELDS)

def solve(columns,target,start,bounds,steps,known_count):
    """Projected coordinate descent; existing quantities stay within ±20% of portion."""
    x=start[:];ridge=.015
    def project(values):
        values=[min(hi,max(lo,v)) for v,(lo,hi) in zip(values,bounds)]
        for i in range(1,known_count+1):values[i]=min(1.2*values[0],max(.8*values[0],values[i]))
        return values
    def prediction(values):return [sum(c[j]*v for c,v in zip(columns,values)) for j in range(4)]
    def loss(values):
        return sum((a-b)**2 for a,b in zip(prediction(values),target))+ridge*sum((a-b)**2 for a,b in zip(values,start))
    x=project(x)
    for _ in range(350):
        old=x[:]
        for i,col in enumerate(columns):
            pred=prediction(x)
            delta=(sum(col[j]*(target[j]-pred[j]) for j in range(4))-ridge*(x[i]-start[i]))/(sum(v*v for v in col)+ridge)
            candidate=x[:];candidate[i]+=delta;candidate=project(candidate)
            if loss(candidate)<=loss(x):x=candidate
        if max(abs(a-b) for a,b in zip(x,old))<1e-6:break
    # Round to usable portions/grams and refine locally without exponential growth.
    x=project([round(v/step)*step for v,step in zip(x,steps)])
    for _ in range(3):
        for i,step in enumerate(steps):
            candidates=[x]
            for direction in (-1,1):
                candidate=x[:];candidate[i]+=direction*step;candidates.append(project(candidate))
            x=min(candidates,key=loss)
    return x

def make_plan(base,rows,known,residual,portion,multipliers,additions,targets):
    portion=round(portion,2)
    factors={r['index']:v for r,v in zip(known,multipliers)}
    ingredients=[]
    actual={k:residual[k]*portion for k in FIELDS}
    for row in rows:
        factor=factors.get(row['index'],portion)
        grams=round(row['baseline_grams']*factor,3) if row['baseline_grams'] is not None else None
        if row['adjustable']:
            for k in FIELDS:actual[k]+=FOODS[row['food_id']][k]*grams/100
        ingredients.append(dict(row,factor=round(factor,4),grams=grams,
                                quantity=round(row['source_quantity']*factor,3) if row['source_quantity'] is not None else None))
    for i,g in additions:
        for k in FIELDS:actual[k]+=FOODS[i][k]*g/100
    energy={k:actual[k]*(9 if k=='fat' else 4) for k in ('protein','fat','carbs')};denominator=sum(energy.values())
    return dict(base=base,portion=portion,targets=targets,actual={k:round(v,2) for k,v in actual.items()},
                difference={k:round(actual[k]-targets[k],2) for k in FIELDS},within_tolerance=reached(actual,targets),
                macro_energy_percent={k:round(v/denominator*100,1) if denominator else 0 for k,v in energy.items()},
                additions=[dict(id=i,name=FOODS[i]['name'],name_en=FOODS[i]['name_en'],grams=round(g,1),
                                nutrition={k:round(FOODS[i][k]*g/100,2) for k in FIELDS}) for i,g in additions if g>0],
                ingredients=ingredients,adjustable_count=len(known),
                quantities_aligned=all(r['quantity_aligned'] for r in rows),
                ingredient_changes=any(abs(factor-portion)>.005 for factor in multipliers))

def adjust(recipe,params):
    base=base_nutrition(recipe);portion=finite(params.get('portion',1),'порция',.25,3)
    rows=composition(recipe,params,FOODS,excluded_food)
    known=[row for row in rows if row['adjustable']]
    contributions=[{k:FOODS[row['food_id']][k]*row['baseline_grams']/100 for k in FIELDS} for row in known]
    residual={k:base[k]-sum(c[k] for c in contributions) for k in FIELDS}
    if any(v < -1e-6 for v in residual.values()):
        raise ValueError('Указанные массы превышают КБЖУ исходной порции. Проверьте граммы и выбранные продукты.')
    residual={k:max(0,v) for k,v in residual.items()}
    mode=params.get('mode','portion')
    if mode=='portion':
        targets={k:base[k]*portion for k in FIELDS}
        return dict(make_plan(base,rows,known,residual,portion,[portion]*len(known),[],targets),suggestions=[],suggest_additions=False)
    if mode!='fit':raise ValueError('Неизвестный способ пересчёта.')
    targets={k:finite(params.get(k,base[k]),k) for k in FIELDS}
    ids=[key for key in params.get('foods','').split(',') if key]
    if len(ids)>3 or len(ids)!=len(set(ids)) or any(key not in FOODS or not FOODS[key]['addition'] for key in ids):
        raise ValueError('Выберите не более трёх разных продуктов из списка.')
    if len({FOODS[key]['group'] for key in ids})!=len(ids):raise ValueError('Выберите по одному продукту из каждой группы.')
    for key in ids:
        if excluded_food(FOODS[key],params.get('exclude','')):raise ValueError(f'Продукт «{FOODS[key]["name"]}» исключён вашим фильтром.')
    scales=(50,5,3,8)
    base_columns=[[residual[k]/s for k,s in zip(FIELDS,scales)]]+[[c[k]/s for k,s in zip(FIELDS,scales)] for c in contributions]
    target=[targets[k]/s for k,s in zip(FIELDS,scales)]
    def fit(addition_ids):
        columns=base_columns+[[FOODS[i][k]/s for k,s in zip(FIELDS,scales)] for i in addition_ids]
        n=len(known)
        x=solve(columns,target,[portion]*(n+1)+[0]*len(addition_ids),
                [(.25,3)]+[(.2,3.6)]*n+[(0,FOODS[i]['max_grams']/100) for i in addition_ids],
                [.05]+[.01]*n+[FOODS[i]['step']/100 for i in addition_ids],n)
        additions=[(i,round(v*100/FOODS[i]['step'])*FOODS[i]['step']) for i,v in zip(addition_ids,x[n+1:])]
        return make_plan(base,rows,known,residual,x[0],x[1:n+1],additions,targets)
    initial=fit([])
    deficits={k:max(0,targets[k]-initial['actual'][k]) for k in FIELDS}
    existing={row['food_id'] for row in rows if row['food_id']}
    available=[f for f in catalog(params.get('exclude','')) if f['addition'] and f['id'] not in existing]
    sweet=bool(re.search(r'dessert|pie|cookie|cake|smoothie|десерт|пирог|печень|смузи|кекс',str(recipe.get('category',''))+' '+str(recipe.get('name','')),re.I))
    dessert={'protein':{'yogurt','cottage','tofu'},'carbs':{'banana','apple','oatmeal'},'fat':{'almonds','walnuts','peanut_butter','sunflower'}}
    savory={'protein':{'chicken','turkey','tuna','shrimp','tofu','lentils','chickpeas'},
            'carbs':{'rice','quinoa','potato','pasta','buckwheat'},'fat':{'oil','avocado','cheddar','sunflower','walnuts'}}
    suggestions=[]
    for group in ('protein','carbs','fat'):
        candidates=[f for f in available if f['group']==group]
        preferred=dessert if sweet else savory
        candidates.sort(key=lambda f:(0 if f['id'] in preferred[group] else 1,-f[group]/max(1,f['calories'])))
        suggestions.extend(candidates[:4])
    allow=params.get('allow_additions','1' if ids else '0')=='1'
    plan=initial
    if not initial['within_tolerance'] and allow:
        groups=[g for g in params.get('auto_groups','').split(',') if g in ('protein','carbs','fat')]
        explicit_groups={FOODS[i]['group'] for i in ids}
        choices=[[f['id'] for f in suggestions if f['group']==g][:2] for g in dict.fromkeys(groups) if g not in explicit_groups]
        choices=[c for c in choices if c]
        combinations=itertools.product(*choices) if choices else [()]
        def error(result):return sum(((result['actual'][k]-targets[k])/s)**2 for k,s in zip(FIELDS,scales))
        for extra in combinations:
            candidate=fit(ids+list(extra))
            if error(candidate)<error(plan):plan=candidate
    return dict(plan,suggestions=[{k:f[k] for k in ('id','name','name_en','group','calories','protein','fat','carbs')} for f in suggestions],
                suggest_additions=not initial['within_tolerance'] and any(deficits[k]>max(1,targets[k]*.05) for k in ('protein','carbs','fat')))
