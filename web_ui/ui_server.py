import flask
from flask import redirect
from flask import url_for

slow_ex_roof_bg = "../static/ventilation_background_slow_ex_roof.jpg"
fast_ex_roof_bg = "../static/ventilation_background_fast_ex_roof.jpg"
slow_ex_lvrm_bg = "../static/ventilation_background_slow_ex_lvrm.jpg"
fast_ex_lvrm_bg = "../static/ventilation_background_fast_ex_lvrm.jpg"
fan_off_bg = "../static/ventilation_background.jpg"
controller = None


"""Create and configure an instance of the Flask application."""
app = flask.Flask(__name__)


@app.route("/")
def show_page():
    global controller
    roof_temp = temp_str(controller.climate_state.roof_data.get_temp())
    lvrm_temp = temp_str(controller.climate_state.lvrm_data.get_temp())
    bdrm_temp = temp_str(controller.climate_state.bdrm_data.get_temp())
    roof_rh = hum_str(controller.climate_state.roof_data.get_humidity())
    lvrm_rh = hum_str(controller.climate_state.lvrm_data.get_humidity())
    bdrm_rh = hum_str(controller.climate_state.bdrm_data.get_humidity())
    target_temp = str(controller.target_temperature)

    flush_button_class = 'buttons'
    if controller.get_hard_flush_requested():
        flush_button_class = 'pending_buttons'

    toggle_enable_value = 'Disable'
    toggle_enable_class = 'buttons'
    diagnostic_button_class = 'hidden_buttons'
    if not controller.enabled:
        toggle_enable_value = 'Enable'
        diagnostic_button_class = 'diagnostic_buttons'
        if controller.hardware_state.state != 'idle':
            toggle_enable_class = 'pending_buttons'

    bg_img = fan_off_bg
    state = controller.hardware_state.state
    if state == 'slow_ex_roof':
        bg_img = slow_ex_roof_bg
    elif state == 'slow_ex_lvrm':
        bg_img = slow_ex_lvrm_bg
    elif state == 'fast_ex_roof':
        bg_img = fast_ex_roof_bg
    elif state == 'fast_ex_lvrm':
        bg_img = fast_ex_lvrm_bg
    return flask.render_template('ventilation.html', background=bg_img, target_temp=target_temp,
                                 roof_temp=roof_temp, roof_hum=roof_rh,
                                 lvrm_temp=lvrm_temp, lvrm_hum=lvrm_rh,
                                 bdrm_temp=bdrm_temp, bdrm_hum=bdrm_rh,
                                 flush_button_class=flush_button_class, toggle_enable_class=toggle_enable_class,
                                 toggle_enable_value=toggle_enable_value,
                                 diagnostic_button_class=diagnostic_button_class)


@app.route('/increase_target', methods=['POST', 'GET'])
def increase_target():
    global controller
    controller.increase_target_temp()
    return redirect(url_for('show_page'))


@app.route('/decrease_target', methods=['POST', 'GET'])
def decrease_target():
    global controller
    controller.decrease_target_temp()
    return redirect(url_for('show_page'))


@app.route('/toggle_enable', methods=['POST', 'GET'])
def toggle_enable():
    global controller
    controller.toggle_enable()
    return redirect(url_for('show_page'))


@app.route('/flush', methods=['POST', 'GET'])
def flush():
    global controller
    controller.request_flush()
    return redirect(url_for('show_page'))


# Handle diagnostic buttons
@app.route('/extract_living', methods=['POST', 'GET'])
def extract_living():
    global controller
    controller.diagnostic_extract_living()
    return redirect(url_for('show_page'))


@app.route('/extract_roof', methods=['POST', 'GET'])
def extract_roof():
    global controller
    controller.diagnostic_extract_roof()
    return redirect(url_for('show_page'))


@app.route('/fan_off', methods=['POST', 'GET'])
def fan_off():
    global controller
    controller.diagnostic_fan_off()
    return redirect(url_for('show_page'))


@app.route('/fan_low', methods=['POST', 'GET'])
def fan_low():
    global controller
    controller.diagnostic_fan_low()
    return redirect(url_for('show_page'))


@app.route('/fan_high', methods=['POST', 'GET'])
def fan_high():
    global controller
    controller.diagnostic_fan_high()
    return redirect(url_for('show_page'))


def temp_str(float_as_str):
    try:
        rounded_float = round(float(float_as_str))
    except TypeError:
        rounded_float = 'err'
    return str(rounded_float) + '°'


def hum_str(float_as_str):
    try:
        rounded_float = round(float(float_as_str))
    except TypeError:
        rounded_float = 'err'
    return str(rounded_float) + '%'


def run_app(_controller):
    global controller
    controller = _controller
    app.run(host='0.0.0.0', debug=False, use_reloader=False)
