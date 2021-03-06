from nltk.inference.resolution import most_general_unification
from nltk.metrics.distance import edit_distance
import requests
from fatsecret import Fatsecret
import nltk

ACCESS_TOKEN_URL = 'https://oauth.fatsecret.com/connect/token'

class Nutrition:
    def __init__(self):
        with open('keys.txt', 'r') as f:
            keys = f.read().splitlines()
        
        self.consumer_key = keys[0]
        self.consumer_secret = keys[1]
        self.fs = Fatsecret(self.consumer_key, self.consumer_secret)
        self.ignore = {
            'measurement_description',
            'metric_serving_amount',
            'metric_serving_unit',
            'number_of_units',
            'serving_description',
            'serving_id',
            'serving_url'
        }
        self.units = {
            'calories' : 'kcal',
            'cholesterol' : 'mg',
            'sodium' : 'mg',
            'potassium' : 'mg',
            'vitamin_d' : 'mcg',
            'vitamin_a' : 'mcg',
            'vitamin_c' : 'mg',
            'calcium' : 'mg',
            'iron' : 'mg'
        }
        self.essential = {
            'calories',
            'carbohydrate',
            'protein',
            'fat',
            'fiber',
            'sugar'
        }

    def get_nutrition_general(self, food):
        food_id = self.fs.foods_search(food)[0]['food_id']
        detailed = self.fs.food_get(food_id)
        name = detailed['food_name'].lower()
        url = detailed['food_url']
        # print(type(detailed['servings']['serving']))
        if isinstance(detailed['servings']['serving'], dict):
            serving = detailed['servings']['serving']
        else:
            serving = detailed['servings']['serving'][0]
        # print(serving)
        serving_desc = serving['serving_description']
        metric = 'g'
        res = f'In {serving_desc} {name} there are:\n'

        info = []
        for key, val in serving.items():
            if key in self.essential:
                unit = self.units[key] if key in self.units else metric
                key2 = 'total ' + key if key == 'carbohydrate' or key == 'fat' else key
                key2 = key2.replace('_', ' ')
                key2 = key2.split()
                key2 = map(lambda x: x.upper() if len(x) == 1 else x, key2)
                key2 = ' '.join(key2)
                info.append(f'{val}{unit} of {key2}')

        info[-1] = 'and ' + info[-1]
        info = ', '.join(info)
        res += info + '\n'
        res += f'More information can be found at {url}'

        return res

    def get_nutrition_specific(self, field, food):
        field = field.lower()
        food_id = self.fs.foods_search(food)[0]['food_id']
        detailed = self.fs.food_get(food_id)
        name = detailed['food_name'].lower()
        url = detailed['food_url']
        if isinstance(detailed['servings']['serving'], dict):
            serving = detailed['servings']['serving']
        else:
            serving = detailed['servings']['serving'][0]
        serving_desc = serving['serving_description']
        serving_desc = serving_desc.replace(name, '')
        metric = 'g'

        keys = list(serving.keys())
        keys = [k for k in keys if k not in self.ignore]
        field = field.replace(' ', '_')

        most_similar, min_dist = None, None
        for k in keys:
            distance = nltk.edit_distance(field, k)
            if most_similar is None or distance < min_dist:
                most_similar, min_dist = k, distance

        res = ""
        if min_dist >= 4:
            res += "The field you want information on may not be in my database for this food...\n"
        desired_val = serving[most_similar]
        unit = self.units[most_similar] if most_similar in self.units else metric
        most_similar = most_similar.replace('_', ' ')
        most_similar = most_similar.split()
        most_similar = map(lambda x: x.upper() if len(x) == 1 else x, most_similar)
        most_similar = ' '.join(most_similar)
        res += f'In {serving_desc} {name} there is {desired_val}{unit} of {most_similar}'
        return res

if __name__ == '__main__':
    nutrition = Nutrition()
    details = nutrition.get_nutrition_general('banana')

    #print(details)

    specific = nutrition.get_nutrition_specific('vitamin c', 'apple')
    print(specific)
    # with open('ignore.txt', 'w') as f2:
    #     f2.write(str(details))

