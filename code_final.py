# ~~~~~IMPORTS~~~~~
import time
import board
import busio
import digitalio
import analogio
import pwmio
import convo as FFF
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

# ~~~~~WIFI STUFF~~~~~
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
# Arduino
esp32_cs = DigitalInOut(board.CS1)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK1, board.MOSI1, board.MISO1)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets)

def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    print("Connected to Adafruit IO! ")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=secrets["aio_username"],
    password=secrets["aio_key"],
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe

# ~~~~~PIN SETTINGS~~~~~
# LEDs
ledR = DigitalInOut(board.D2)
ledR.direction = digitalio.Direction.OUTPUT
ledY = DigitalInOut(board.D3)
ledY.direction = digitalio.Direction.OUTPUT
ledG = DigitalInOut(board.D4)
ledG.direction = digitalio.Direction.OUTPUT
# WATER PUMP
pump = digitalio.DigitalInOut(board.A1)
pump.direction = digitalio.Direction.OUTPUT
# MOISTURE SENSOR
Moisture = analogio.AnalogIn(board.A0)
# BUZZER
buzzer = pwmio.PWMOut(board.D5, variable_frequency=True)


# ~~~~~FUNCTIONS~~~~~
# Buzzer song fx
def note(name):
    # Returns code understandable note (Hz)
    octave = int(name[-1])
    PITCHES = "c,c#,d,d#,e,f,f#,g,g#,a,a#,b".split(",")
    pitch = PITCHES.index(name[:-1].lower())
    return 440 * 2 ** ((octave - 4) + (pitch - 9) / 12.)
sequence = [
   ("g4", 2), ("g5", 5.5), ("e5", 0.5), ("d5", 1.5), ("c5", 0.5), ("a4", 6), ("g4", 2),
   ("c5", 5.5), ("c5", 0.5), ("d5", 1.5), ("e5", 0.5), ("g5", 6), ("g4", 1.5),
   ("a4", 0.5), ("c5", 5.5), ("d5", 0.5), ("e5", 2), ("g5", 4), ("e2", 2), ("g5", 2),
   ("g5", 5.5), ("e5", 0.5), ("d5", 2), ("a4", 6), (None, 2)]

# Moisture Sensing
def get_moisture(pin):
    # Get reading from moisture sensor
    return pin.value

# Communicating with WaterPump
def on_water_msg(client, topic, message):
    # Method called whenever user/feeds/water has a new value
    print("New message on topic {0}: {1} ".format(topic, message))
    if message == "0":
        pump.value = True
        time.sleep(5)
        pump.value = False
        time.sleep(2)
        buzzer.duty_cycle = 2**15
        for i in (1 , 2 , 3):
            for (notename, eighths) in sequence:
                length = eighths * 0.1
                if notename:
                    note_play = note(notename)
                    buzzer.frequency = round(note_play)
                    time.sleep(length)
                else:
                    time.sleep(length)
        buzzer.duty_cycle = 0
    elif message == "1":
        pump.value = False
    else:
        print("Unexpected message on water feed.")

# Sharing random coriander facts on the press of a button
def on_conversation_msg(client, topic, message):
    # Method called whenever user/feeds/conversation has a new value (when the button is pressed)
    print("New message on topic {0}: {1} ".format(topic, message))
    if message == "Give me a fact!":
        fact = FFF.fact_finder()
        io.publish("conversation", fact)
        print("Fact published")
        time.sleep(1)
    elif message == "Tell me a joke!":
        joke = FFF.joke_teller()
        io.publish("conversation", joke)
        print("Joke Told")
        time.sleep(1)
    elif message == "Recipe Ideas":
        recipe = FFF.recipe_list()
        io.publish("conversation", recipe)
        print("Recipe Shared")
        time.sleep(1)
    elif message == "---------":
        print("Button back to neutral")
        time.sleep(1)

def sing_to_me(client, topic, message):
    # Method called whenever user/feeds/Buzzer has a new value
    print("New message on topic {0}: {1} ".format(topic, message))
    if message == "0":
        buzzer.duty_cycle = 2**15
        for i in (1, 2):
            for (notename, eighths) in sequence:
                length = eighths * 0.1
                if notename:
                    note_play = note(notename)
                    buzzer.frequency = round(note_play)
                    time.sleep(length)
                else:
                    time.sleep(length)
        buzzer.duty_cycle = 0
    elif message == "1":
        pump.value = False
    else:
        print("Unexpected message on Buzzer feed.")


# ~~~~~Estableciendo conexion~~~~~
# Set up a callback for the WaterPump feed
io.add_feed_callback("conversation", on_conversation_msg)
io.add_feed_callback("water", on_water_msg)
io.add_feed_callback("buzzer", sing_to_me)

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

# Subscribe to all message feeds
io.subscribe("water")
io.subscribe("conversation")
io.subscribe("buzzer")

# ~~~~~MAIN LOOP~~~~~
prv_refresh_time = 0.0
needs_water = False
initial = time.monotonic()
x = time.monotonic()
timer = True


while True:
    try:
        io.loop()
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        wifi.connect()
        io.reconnect()
        continue

    now = time.monotonic()
    if now > initial + (20):                     # Records moisture lvl every 15mins
        return_val = get_moisture(Moisture)
        percent_moist = (return_val/40000)*100
        print("Moisture Reading", return_val)
        print("Moisture Percentage", percent_moist)
        io.publish("moisture", percent_moist)
        print("Published")
        initial = time.monotonic()

        if percent_moist < 40 and timer:
            # If moisture limit reached, needs_water becomes true
            needs_water = True
            # dry_time has been recorded and plant needs_water so a message sent in 1h
            dry_time = time.monotonic()
            ledR.value = True
            ledY.value = False
            ledG.value = False
            timer = False

        if percent_moist < 60 and percent_moist > 40 :
            ledR.value = False
            ledY.value = True
            ledG.value = False

        if percent_moist > 60:
            ledR.value = False
            ledY.value = False
            ledG.value = True
            print('i am moist')

        if needs_water and now > (dry_time + 40):
            print('I need water please')       # Send message/email/tweet
            timer = True
            needs_water = False
            # Add other features for when needs_water
