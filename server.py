from flask import Flask, request, jsonify
import json
import requests
from difflib import SequenceMatcher

SEARCH_VARIANTS_URL = "http://kimaorg.azurewebsites.net/api/Variants/SearchVariants/{query}/100/1"
PLACE_URL = "http://kimaorg.azurewebsites.net/api/Places/Place/{place_id}"

app = Flask(__name__)
address = '0.0.0.0'
port = '3200'

PLACE_TYPE = {"id": "T1", "name": "Place"}
PROPERTIES_MAPPING = {
    "P2": {
        "id": "viaF_ID",
        "name": "VIAF ID"},
    "P3": {
        "id": "geoname_ID",
        "name": "GeoName ID"},
    "P6": {
        "id": "country_code",
        "name": "GN Modern Country Code"},
    "P8": {
        "id": "language",
        "name": "Language"},
    "P9": {
        "id": "wd",
        "name": "WikiData ID"},
    "P10": {
        "id": "modernCountry",
        "name": "Modern Country"},
    "P11": {
        "id": "yid",
        "name": "Yidish Name"},
    "P12": {
        "id": "desc",
        "name": "Description"},
    "P13": {
        "id": "coor",
        "name": "Coordinates"},
    "P14": {
        "id": "primary_rom_full",
        "name": "Primary Roman Name"}
}
properties_l = []
[properties_l.append({"id": key, "name": PROPERTIES_MAPPING[key]["name"]}) for key in PROPERTIES_MAPPING.keys()]


def search_entity(query, properties_q=[]):
    matches = []
    res = requests.get(SEARCH_VARIANTS_URL.format(query=query))
    if res.status_code != 200:
        return []

    json_res = res.json()
    # no match
    if not json_res:
        return []

    if properties_q:
        return search_entity_with_props(properties_q, json_res)

    num_of_matches = len(json_res)
    if num_of_matches == 1:
        return [{
            "id": str(json_res[0]["placeId"]),
            "name": str(json_res[0]["primary_heb_full"]),
            "score": 100.0,
            "match": True,
            "type": [PLACE_TYPE]}]

    for match in json_res:
        entity_id = match["placeId"]
        res_to_add = {
            "id": str(entity_id),
            "name": str(match["primary_heb_full"]),
            "score": 100.0 / num_of_matches,
            "match": False,
            "type": [PLACE_TYPE]}
        matches.append(res_to_add)

    return sorted(matches, key=lambda k: k['name'])


def search_entity_with_props(properties_q, json_res):
    matches = []
    max_ratios = max_prop_match_ratio(properties_q, json_res)
    properties_match = []
    [properties_match.append(num_of_prop_match(idx, max_ratios)) for idx, match in enumerate(json_res)]
    max_matches = max(properties_match)
    num_of_max = properties_match.count(max_matches)
    max_index = properties_match.index(max_matches)
    for idx, match in enumerate(json_res):
        entity_id = match["placeId"]
        score = (properties_match[idx] / len(properties_q))
        res_to_add = {
            "id": str(entity_id),
            "name": str(match["primary_heb_full"]),
            "score": 100.0 * score,
            "match": idx == max_index and num_of_max == 1,
            "type": [PLACE_TYPE]}
        matches.append(res_to_add)
    return sorted(matches, key=lambda k: k['score'], reverse=True)


def prop_match_ratio(entity_id, prop):
    entity_res = get_entity_res(entity_id)
    prop_id = prop["pid"]
    prop_val = prop["v"]
    return SequenceMatcher(None, entity_res[PROPERTIES_MAPPING[prop_id]["id"]], prop_val).ratio()


def max_prop_match_ratio(properties_q, json_res):
    winning_match = []
    for prop in properties_q:
        ratios = []
        for match in json_res:
            ratios.append(prop_match_ratio(match["placeId"], prop))
        max_ratio = max(ratios)
        winning_match.append([{idx: ratio} for idx, ratio in enumerate(ratios) if ratio == max_ratio])

    return winning_match


def num_of_prop_match(idx, max_ratios):
    count = 0
    for matches in max_ratios:
        for winning_matchts in matches:
            if idx in winning_matchts:
                count = count + 1
    return count

def jsonpify(obj):
    try:
        callback = request.args['callback']
        response = app.make_response("%s(%s)" % (callback, json.dumps(obj)))
        response.mimetype = "text/javascript"
        return response
    except KeyError:
        return jsonify(obj)


def get_entity_res(entity_id):
    res = requests.get(PLACE_URL.format(place_id=entity_id))
    json_res = res.json()
    return json_res


def get_entity_prop_res(entity_res, prop):
    key_from_res = PROPERTIES_MAPPING[prop]["id"]
    return entity_res[key_from_res]


def handle_queries(queries):
    queries = json.loads(queries)
    results = {}
    for (query_key, query) in queries.items():
        properties_q = query.get('properties')
        if properties_q:
            res = search_entity(query['query'], properties_q)
        else:
            res = search_entity(query['query'])
        results[query_key] = {"result": res}

    return jsonpify(results)


def handle_extend(extend):
    rows = "rows"
    meta = "meta"

    extend = list(json.loads(extend).items())

    (_, listIds) = extend[0]
    (_, propertiesIds) = extend[1]

    results = {meta: [], rows: {}}
    for propObject in propertiesIds:
        prop = propObject['id']
        results[meta].append({
            "id": prop,
            "name": PROPERTIES_MAPPING[prop]["name"]
        })

    for item_id in listIds:
        entity_res = get_entity_res(item_id)
        results[rows][item_id] = {}
        for propObject in propertiesIds:
            prop = propObject['id']
            prop_res = get_entity_prop_res(entity_res, prop)

            if not prop_res:
                results[rows][item_id][prop] = []
            else:
                results[rows][item_id][prop] = [{"str": prop_res}]

    return jsonpify(results)


@app.route('/api', methods=['GET', 'POST'])
def main():
    domain = 'http://' + request.host
    generic = {
        'name': 'KIMA',
        'identifierSpace': 'http://rdf.freebase.com/ns/type.object.id',
        'schemaSpace': 'http://rdf.freebase.com/ns/type.object.id',
        'view': {
            'url': 'http://kimaorg.azurewebsites.net/Places/Details?id={{id}}'
        },
        "defaultTypes": [],
        "extend": {
            "propose_properties":
                {
                    "service_url": domain + "/propose_properties",
                    "service_path": "/heb"
                },
        },
        "suggest": {
            "property": {
                    "service_url": domain + "/property",
                    "service_path": "/search"
            }
        }
    }
    queries = request.form.get('queries')
    extend = request.form.get('extend')

    if queries:
        return handle_queries(queries)

    if extend:
        return handle_extend(extend)

    return jsonpify(generic)


@app.route('/propose_properties/heb', methods=['GET'])
def properties():
    res = {
        "type": "Q1549591",
        "properties": properties_l
    }

    return jsonpify(res)


@app.route('/property/search', methods=['GET'])
def search_property():
    prefix = request.args.get('prefix')
    if not prefix:
        return jsonpify({"result": []})

    matches = []
    for (property_id, property_val) in PROPERTIES_MAPPING.items():
        if prefix in property_val["id"] or prefix in property_val["name"]:
            matches.append({
                "name": property_val["name"],
                "id": property_id
            })

    return jsonpify({"result": matches})


if __name__ == '__main__':
    app.run(address, port, True)

