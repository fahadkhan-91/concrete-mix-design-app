from flask import Flask, render_template, request
from logic.mix_design import calculate_mix

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', result=None)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = {
            'fck': float(request.form['fck']),          # target strength MPa
            'slump': int(request.form['slump']),         # mm
            'max_agg_size': int(request.form['max_agg_size']),  # mm
            'exposure': request.form['exposure'],         # mild/moderate/severe
            'fm_sand': float(request.form['fm_sand']),    # fineness modulus of sand
        }
        result = calculate_mix(data)
    except Exception as e:
        result = {'error': str(e)}

    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
