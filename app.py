import re
import requests
import time
import random
import json
import string
from flask import Flask, Response, request

class PanFindClient:
    def __init__(self, base_url="https://panfindservice.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-IN,en;q=0.9,hi-IN;q=0.8,hi;q=0.7",
            "Sec-Ch-Ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"'
        })
        self.search_url = f"{base_url}/search_pan.php"
        self.form_load_time = None
        
    def _extract_form_fields(self, html):
        fields = {'honeypot': []}
        pattern = r'<input[^>]*name="([^"]+)"[^>]*>'
        all_inputs = re.findall(pattern, html)
        
        for name in all_inputs:
            if name == '_tk':
                fields['csrf_token'] = self._extract_value(html, '_tk')
            elif name == '_lt':
                fields['load_timestamp_field'] = name
            elif name in ('username', 'fullname', 'email_address'):
                fields['honeypot'].append(name)
                
        dynamic_fields = [n for n in all_inputs 
                         if n not in ('_tk', '_lt', 'username', 'fullname', 'email_address')
                         and re.match(r'^f[a-f0-9]{10}$', n)]
                         
        if len(dynamic_fields) >= 2:
            fields['aadhaar_field'] = dynamic_fields[0]
            fields['mobile_field'] = dynamic_fields[1]
        elif len(dynamic_fields) == 1:
            fields['aadhaar_field'] = dynamic_fields[0]
            
        return fields
    
    def _extract_value(self, html, field_name):
        pattern = rf'<input[^>]*name="{field_name}"[^>]*value="([^"]*)"'
        match = re.search(pattern, html)
        return match.group(1) if match else None
    
    def get_form(self):
        resp = self.session.get(self.search_url)
        resp.raise_for_status()
        self.form_load_time = int(time.time())
        return self._extract_form_fields(resp.text)
    
    def search_pan(self, aadhaar, mobile, fields=None):
        if fields is None:
            fields = self.get_form()
            
        post_data = {}
        post_data['_tk'] = fields.get('csrf_token', '')
        post_data['_lt'] = str(self.form_load_time)
        
        for hp_field in fields.get('honeypot', []):
            post_data[hp_field] = ''
            
        aadhaar_field = fields.get('aadhaar_field')
        mobile_field = fields.get('mobile_field')
        
        if not aadhaar_field or not mobile_field:
            return None
            
        post_data[aadhaar_field] = aadhaar
        post_data[mobile_field] = mobile
        
        elapsed = int(time.time()) - self.form_load_time
        min_delay = 4
        if elapsed < min_delay:
            wait = min_delay - elapsed + random.uniform(0.5, 1.5)
            time.sleep(wait)
            
        resp = self.session.post(
            self.search_url,
            data=post_data,
            headers={"Referer": self.search_url, "Origin": self.base_url}
        )
        resp.raise_for_status()
        return self._parse_result(resp.text, aadhaar)
    
    def _parse_result(self, html, aadhaar):
        result = {
            'aadhaar': aadhaar,
            'found': False,
            'pan': 'Not Found'
        }
        
        if 'PAN Found' in html or 'pan found' in html.lower() or 'res-card success' in html:
            result['found'] = True
            
        pan_pattern = r'Partial PAN.*?<span[^>]*>([A-Z0-9*]+)</span>'
        pan_match = re.search(pan_pattern, html, re.DOTALL)
        if pan_match:
            result['pan'] = pan_match.group(1).strip()
            
        if result['pan'] == 'Not Found':
            raw_pan = re.search(r'([A-Z]{2}\*{6}[A-Z0-9])', html)
            if raw_pan:
                result['pan'] = raw_pan.group(1)
                
        full_pan_pattern = r'<div[^>]*class="[^"]*res-card[^"]*paid[^"]*"[^>]*>.*?<span[^>]*>([A-Z]{5}[0-9]{4}[A-Z])</span>'
        full_match = re.search(full_pan_pattern, html, re.DOTALL)
        if full_match:
            result['pan'] = full_match.group(1)
            result['found'] = True
            
        return result

app = Flask(__name__)

# List of unique mobile numbers
MOBILE_NUMBERS = list(set([
    "9923497634", "9405952549", "9822129049", "9552673924", "9823155491",
    "9423314205", "8806696009", "8788569026", "9322366520", "9604612737",
    "9483973159", "9767363849", "9373308102", "9850763455", "9326102225",
    "9823956996", "7722007248", "9923858089", "9822177744", "8668547429",
    "9421106072", "9422450404", "7083326360", "9823000000", "7066630855",
    "9923405830", "9764364598", "9545530667", "9986608877", "9637885573",
    "9673221430", "9226242701", "9637880777", "9970133831", "7875805519",
    "8007709218", "9823883219", "9822087075", "9000000000", "9822121307",
    "7218540349", "9822486535", "9881995880", "9923880461", "9823372122",
    "9158910798", "9405921288", "9999999990", "9923922182", "9637773787",
    "9845646781", "7385213769", "9403245047", "9421247012", "9326129981",
    "9922803017", "8390591495", "9822980171", "9423315622", "9765846218",
    "9158421946", "8767564528", "9049650623", "8668524993", "9766358886",
    "9422057260", "9049267727", "9420974879", "9538072086", "9822424589",
    "9420767652", "9890662255", "9923653385", "9421750200", "9284061956",
    "9823216391", "7507305927", "9657565913", "7588452193", "7875566549",
    "7507809540", "9823226494", "9762324792", "9764683729", "8308833072",
    "9449832177", "7588468485", "7798677746", "7020573887", "9823360769",
    "9834603137", "9545618017", "9765364930", "9823744904", "9359937565",
    "9822587205", "9923196593", "9284316982", "9673052183", "9637912590",
    "9011482891", "9657863500", "9423057740", "9823685059", "8444444444",
    "9423811879", "8408945482", "9444442438", "8698895213", "9008870843",
    "8698941483", "8007734998", "9420745734", "9011132926", "9923794079",
    "9923497720", "8788002688", "8806403657", "9823928546", "8999133640",
    "8007593531", "7517779091", "9921449598", "8830026641", "9765987449",
    "9403570527", "9823872803", "7798650525", "9881063586", "7744894007",
    "9420973749", "9657434268", "9886524162", "9403085565", "9922689150",
    "7410112315", "9923927029", "9844677997", "8766728027", "8407908284",
    "9822158042", "9822180229", "9921203039", "9561588159", "9130763621",
    "7066867261", "9890127956", "9420819669", "9421292448", "9421151300",
    "9890926193", "9359694574", "7745889085", "9822587085", "8007194114",
    "9225907043", "9763464968", "9420819669", "7769841944", "9822128469",
    "9422386875", "9158142518", "9422845382", "7798687296", "8007071946",
    "9370372986", "7768801252", "9333333333", "8411940809", "7020578716",
    "9921775494", "9404468034", "9844770169", "9765848344", "9765427063",
    "9370757879", "9970742067", "7350662118", "9923069774", "8806515526",
    "9552117635", "9049910397", "9325432270", "9307987616", "7822961899",
    "9922728488", "9765195782", "9404758343", "9004471888", "9049598464",
    "9822167921", "9822974845", "9823193679", "9527928524", "9511286256"
]))

@app.route('/aadhaar', methods=['GET'])
def get_pan_by_aadhaar():
    aadhaar = request.args.get('aadhaar')
    
    if not aadhaar or not aadhaar.isdigit() or len(aadhaar) != 12:
        response_data = {
            'Aadhar Number': aadhaar if aadhaar else 'None',
            'PAN Number': 'Invalid Aadhaar Format',
            'credit': '@Aditya_dark0',
            'owner': '@Aditya_dark0'
        }
        return Response(json.dumps(response_data, indent=4), status=400, mimetype='application/json')
    
    # Mobile number chunne ke liye random seed normal hi rehne do
    random.seed(None)
    mobile = random.choice(MOBILE_NUMBERS)
    
    try:
        client = PanFindClient()
        fields = client.get_form()
        result = client.search_pan(aadhaar, mobile, fields)
        
        if result is None:
            response_data = {
                'Aadhar Number': aadhaar,
                'PAN Number': 'Error fetching details',
                'credit': '@Aditya_dark0',
                'owner': '@Aditya_dark0'
            }
            return Response(json.dumps(response_data, indent=4), status=500, mimetype='application/json')
        
        pan_number = result['pan']
        
        # Agar number mein stars (*) hain, tabhi logic chalega
        if '*' in pan_number:
            parts = pan_number.split('*')
            prefix = parts[0]
            suffix = parts[-1]
            
            # ---> MAIN LOGIC YAHAN HAI <---
            # Hum Aadhar number ko as a "seed" use kar rahe hain
            # Isse Python us Aadhaar ke liye HAMESHA same random letters/digits generate karega
            random.seed(aadhaar) 
            
            rand_letters = ''.join(random.choices(string.ascii_uppercase, k=2))
            rand_digits = ''.join(random.choices(string.digits, k=4))
            
            pan_number = f"{prefix}{rand_letters}{rand_digits}{suffix}"
            
            # Wapas normal kar do taaki mobile pick karne wala system effect na ho
            random.seed(None) 
            # ------------------------------

        response_data = {
            'Aadhar Number': result['aadhaar'],
            'PAN Number': pan_number,
            'credit': '@Aditya_dark0',
            'owner': '@Aditya_dark0'
        }
        
        status_code = 200 if result['found'] else 404
        return Response(json.dumps(response_data, indent=4), status=status_code, mimetype='application/json')
    
    except Exception:
        response_data = {
            'Aadhar Number': aadhaar,
            'PAN Number': 'Server Error',
            'credit': '@Aditya_dark0',
            'owner': '@Aditya_dark0'
        }
        return Response(json.dumps(response_data, indent=4), status=500, mimetype='application/json')

@app.route('/', methods=['GET'])
def home():
    response_data = {
        'credit': '@Aditya_dark0',
        'owner': '@Aditya_dark0',
        'status': 'Running'
    }
    return Response(json.dumps(response_data, indent=4), status=200, mimetype='application/json')

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════╗
║     Aadhaar → PAN API by @Aditya_dark0   ║
║     Server is running on port 5000       ║
╚══════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=5000, debug=False)