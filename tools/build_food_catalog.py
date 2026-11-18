"""Build the small food reference from the public USDA SR28 abbreviated file."""
import argparse
import csv
import io
import json
import urllib.request
from pathlib import Path
from zipfile import ZipFile

SOURCE='https://www.ars.usda.gov/ARSUserFiles/80400535/DATA/SR/sr28/dnload/sr28abbr.zip'
# id, NDB number, group, Russian label, English label, tags, exact ingredient aliases,
# maximum added grams, eligible as a suggested ready-to-eat addition.
SELECTED=[
 ('chicken','05064','protein','Куриная грудка, готовая','Cooked chicken breast','chicken poultry meat курица курицы курицей мясо птица',['cooked chicken breast','cooked chicken'],200,True),
 ('yogurt','01256','protein','Греческий йогурт без добавок, 0%','Plain Greek yogurt, 0% fat','yogurt milk dairy lactose йогурт молоко молочные молочки лактоза',['plain greek yogurt','greek yogurt'],300,True),
 ('rice','20045','carbs','Рис белый, варёный','Cooked white rice','rice рис риса рисом',['cooked rice','cooked white rice','вареный рис'],300,True),
 ('banana','09040','carbs','Банан без кожуры','Peeled banana','banana bananas банан банана бананы',['banana','bananas','банан'],200,True),
 ('oil','04053','fat','Оливковое масло','Olive oil','olive oil vegetable fat масло оливковое масла',['olive oil','оливковое масло'],30,True),
 ('almonds','12061','fat','Миндаль','Almonds','almond almonds nut nuts миндаль орехи орехов',['almonds','almond','миндаль'],40,True),
 ('turkey','05220','protein','Грудка индейки, готовая','Roasted turkey breast','turkey poultry meat индейка индейки мясо птица',['cooked turkey breast'],200,True),
 ('tuna','15121','protein','Тунец в воде, без жидкости','Canned tuna in water, drained','tuna fish seafood тунец рыба рыбы морепродукты',['canned tuna','tuna in water'],200,True),
 ('egg','01129','protein','Яйцо варёное','Hard-boiled egg','egg eggs яйцо яйца яиц',['hard-boiled eggs','boiled egg'],150,True),
 ('tofu','16426','protein','Тофу твёрдый','Firm tofu','tofu soy soya soybean тофу соя соевый',['firm tofu','tofu'],250,True),
 ('cottage','01016','protein','Творог зернёный, 1%','Cottage cheese, 1% fat','cottage cheese milk dairy lactose творог сыр молоко молочные лактоза',['cottage cheese'],250,True),
 ('lentils','16070','protein','Чечевица варёная','Cooked lentils','lentil lentils legume legumes чечевица бобовые',['cooked lentils'],250,True),
 ('chickpeas','16057','protein','Нут варёный','Cooked chickpeas','chickpea chickpeas garbanzo legume legumes нут бобовые',['cooked chickpeas','cooked garbanzo beans'],250,True),
 ('shrimp','15151','protein','Креветки, готовые','Cooked shrimp','shrimp prawns shellfish seafood креветки морепродукты',['cooked shrimp'],200,True),
 ('buckwheat','20010','carbs','Гречка варёная','Cooked buckwheat','buckwheat гречка гречневая крупа',['cooked buckwheat'],300,True),
 ('quinoa','20137','carbs','Киноа варёная','Cooked quinoa','quinoa киноа',['cooked quinoa'],300,True),
 ('potato','11367','carbs','Картофель отварной','Boiled potato','potato potatoes картофель картошка',['boiled potatoes','boiled potato'],300,True),
 ('pasta','20121','carbs','Макароны варёные','Cooked pasta','pasta spaghetti wheat gluten макароны паста пшеница глютен',['cooked pasta','cooked spaghetti'],250,True),
 ('oatmeal','08121','carbs','Овсяная каша на воде','Oatmeal cooked in water','oat oats oatmeal овес овсянка овсяная',['cooked oatmeal'],300,True),
 ('apple','09003','carbs','Яблоко с кожурой','Apple with skin','apple apples яблоко яблоки',['apple','apples'],250,True),
 ('avocado','09037','fat','Авокадо','Avocado','avocado авокадо',['avocado','avocados'],150,True),
 ('walnuts','12155','fat','Грецкие орехи','Walnuts','walnut walnuts nut nuts грецкий грецкие орех орехи',['walnuts','walnut'],40,True),
 ('sunflower','12036','fat','Семечки подсолнечника','Sunflower kernels','sunflower seed seeds семечки подсолнечник семена',['sunflower seeds','sunflower kernels'],40,True),
 ('peanut_butter','16098','fat','Арахисовая паста','Peanut butter','peanut peanuts butter nut nuts арахис арахисовая орех орехи',['peanut butter'],40,True),
 ('cheddar','01009','fat','Сыр чеддер','Cheddar cheese','cheddar cheese milk dairy lactose чеддер сыр молоко молочные лактоза',['cheddar cheese','cheddar'],60,True),
 ('raw_chicken','05062','protein','Куриная грудка, сырая','Raw chicken breast','chicken poultry meat курица курицы курицей мясо птица',['chicken breast','skinless chicken breast','boneless skinless chicken breasts'],200,False),
 ('raw_rice','20044','carbs','Рис длиннозёрный, сухой','Dry long-grain rice','rice рис риса рисом',['long-grain rice','uncooked rice','white rice'],150,False),
 ('flour','20081','carbs','Мука пшеничная','All-purpose wheat flour','flour wheat gluten мука пшеница глютен',['all-purpose flour','flour','wheat flour'],100,False),
 ('sugar','19335','carbs','Сахар','Granulated sugar','sugar sugars сахар',['sugar','granulated sugar'],40,False),
 ('milk','01079','protein','Молоко, 2%','Milk, 2% fat','milk dairy lactose молоко молочные лактоза',['milk','2% milk'],300,False),
 ('raw_egg','01123','protein','Яйцо сырое','Raw egg','egg eggs яйцо яйца яиц',['eggs','egg'],150,False),
 ('butter','01001','fat','Масло сливочное','Butter','butter milk dairy lactose масло сливочное молоко молочные лактоза',['butter','salted butter'],30,False),
 ('mushroom','11260','protein','Шампиньоны сырые','Raw white mushrooms','mushroom mushrooms грибы гриб шампиньоны',['fresh mushrooms','mushrooms','white mushrooms'],300,False),
 ('onion','11282','carbs','Лук репчатый','Raw onion','onion onions лук',['onion','onions'],200,False),
 ('broccoli','11090','carbs','Брокколи сырая','Raw broccoli','broccoli брокколи',['broccoli'],300,False),
]

def build(archive):
    with ZipFile(archive) as z:
        rows={r[0]:r for r in csv.reader(io.StringIO(z.read('ABBREV.txt').decode('cp1252')),delimiter='^',quotechar='~')}
    result={}
    for key,ndb,group,name,name_en,tags,aliases,maximum,addition in SELECTED:
        r=rows[ndb]
        result[key]=dict(name=name,name_en=name_en,group=group,calories=float(r[3]),protein=float(r[4]),
                         fat=float(r[5]),carbs=float(r[7]),max_grams=maximum,step=1 if group=='fat' else 5,
                         ndb=ndb,tags=tags,aliases=aliases,addition=addition,source=SOURCE,source_description=r[1])
    output=Path(__file__).resolve().parents[1]/'data'/'nutrition_foods.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Saved {len(result)} USDA reference foods: {output}')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    if args.archive:build(args.archive)
    else:
        with urllib.request.urlopen(SOURCE,timeout=30) as response:build(io.BytesIO(response.read()))
