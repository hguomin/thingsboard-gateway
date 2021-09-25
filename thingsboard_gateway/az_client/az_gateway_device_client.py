#     Copyright 2021. Guomin Huang
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import ssl
import time
import logging
import random
from paho.mqtt import client as mqtt
from simplejson import dumps

from thingsboard_gateway.tb_client.tb_device_mqtt import TBPublishInfo, TBQoSException

class AzGatewayDeviceClient:
    def __init__(self, iothub_host, device_id, sas_token, ca_cert, connect_callback=None, disconnect_callback=None):
        self._iothub_host = iothub_host
        self._port = 8883
        self._device_id = device_id
        self._on_connect_callback = connect_callback
        self._on_disconnect_callback = disconnect_callback

        self._client = mqtt.Client(device_id)
        
        self._client.on_connect =  self._on_connect
        self._client.on_disconnect = self._on_disconnect

        self._client.username_pw_set(iothub_host + "/" + device_id, sas_token)
        try:
            self._client.tls_set(ca_cert, None, None, ssl.CERT_REQUIRED, ssl.PROTOCOL_TLSv1_2, None)
        except Exception as e:
            print(e)

        self._client.tls_insecure_set(False)

        self._topic_d2c = "devices/" + device_id + "/messages/events/"
        self._topic_device_twin_result = "$iothub/twin/res/#"
        self._topic_device_twin_update = "$iothub/twin/PATCH/properties/reported/?$rid="

        self._connect_callback = None
        self._is_connected = False

        self._log = logging.getLogger("AzGatewayDeviceClient")

        self.quality_of_service = 1

    def connect(self, callback=None, min_reconnect_delay=1, timeout=120, keepalive=120):
        try:
            self._client.connect(self._iothub_host, self._port)
        except Exception as e:
            print(e)
        #self.reconnect_delay_set(min_reconnect_delay, timeout)
        self._client.loop_start()
        self._connect_callback = callback

    def _on_connect(self, client, userdata, flags, result_code, *extra_params):
        result_codes = {
            1: "incorrect protocol version",
            2: "invalid client identifier",
            3: "server unavailable",
            4: "bad username or password",
            5: "not authorised",
        }
        if self._connect_callback:
            time.sleep(.05)
            self._connect_callback(client, userdata, flags, result_code, *extra_params)

        if( self._on_connect_callback is not None):
            self._on_connect_callback(client, userdata, flags, result_code, *extra_params)

        if result_code == 0:
            self._is_connected = True
            self._client.subscribe(self._topic_device_twin_result)
            self._log.info("connection SUCCESS")
        else:
            if result_code in result_codes:
                self._log.error("connection FAIL with error %s %s", result_code, result_codes[result_code])
            else:
                self._log.error("connection FAIL with unknown error")

    def disconnect(self):
        self._client.disconnect()
        self._log.debug("Disconnecting from IoT Hub")
        self._is_connected = False
        self._client.loop_stop()

    def _on_disconnect(self, client, userdata, result_code):
        if( self._on_disconnect_callback is not None):
            self._on_disconnect_callback(client, userdata, result_code)

        self._log.debug("Disconnected client: %s, user data: %s, result code: %s", str(client), str(userdata), str(result_code))

    def is_connected(self):
        return self._is_connected

    def _on_publish(self, client, userdata, result):
        pass

    def _on_message(self, client, userdata, message):
        self._log.info(message)

    def publish_data(self, data, topic, qos):
        data = dumps(data)
        if qos is None:
            qos = self.quality_of_service
        if qos not in (0, 1):
            self._log.exception("Quality of service (qos) value must be 0 or 1")
            raise TBQoSException("Quality of service (qos) value must be 0 or 1")
        
        ret = self._client.publish(topic, data, qos)

        return TBPublishInfo(ret)

    def send_telemetry(self, telemetry, qos=None):
        msg_data = {}
        msg_data["deviceId"] = self._device_id
        msg_data["source"] = "gateway"
        if not isinstance(telemetry, list) and not (isinstance(telemetry, dict) and telemetry.get("ts") is not None):
            telemetry = [telemetry]
        msg_data["content"] = {"telemetry": telemetry}

        return self.publish_data(msg_data, self._topic_d2c, self._get_qos(qos))

    def send_attributes(self, attributes, qos=None):
        msg_data = {}
        msg_data["deviceId"] = self._device_id
        msg_data["source"] = "gateway"
        msg_data["content"] = {"attribute": attributes}

        return self.publish_data(msg_data, self._topic_d2c, self._get_qos(qos))

    def gw_send_telemetry(self, device, telemetry, qos=1):
        msg_data = {}
        msg_data["deviceId"] = device
        msg_data["source"] = "device"
        msg_data["content"] = {"telemetry": telemetry} 
        
        return self.publish_data(msg_data, self._topic_d2c, qos)

    def gw_send_attributes(self, device, attributes, qos=1):
        msg_data = {}
        msg_data["deviceId"] = device
        msg_data["source"] = "device"
        msg_data["content"] = {"attribute": attributes}

        return self.publish_data(msg_data, self._topic_d2c, qos)

    def _get_qos(self, qos=None):
        return qos if qos is not None else self.quality_of_service

    def reconnect_delay_set(self, min_delay=1, max_delay=120):
        """The client will automatically retry connection. Between each attempt it will wait a number of seconds
         between min_delay and max_delay. When the connection is lost, initially the reconnection attempt is delayed
         of min_delay seconds. It’s doubled between subsequent attempt up to max_delay. The delay is reset to min_delay
          when the connection complete (e.g. the CONNACK is received, not just the TCP connection is established)."""
        self._client.reconnect_delay_set(min_delay, max_delay)


    #Not support for below features yet in iot hub
    def gw_connect_device(self, device_name, device_type):
        self._log.error("gw_connect_device is not supported in AzGatewayDeviceClient")
        raise NotImplementedError
        #return TBPublishInfo()

    def gw_disconnect_device(self, device_name):
        self._log.error("gw_disconnect_device is not supported in AzGatewayDeviceClient")
        raise NotImplementedError
        #return TBPublishInfo()

    def get_subscriptions_in_progress(self):
        self._log.error("get_subscriptions_in_progress is not supported in AzGatewayDeviceClient")
        return False
    def clean_device_sub_dict(self):
        self._log.error("clean_device_sub_dict is not supported in AzGatewayDeviceClient")
        
    def gw_set_server_side_rpc_request_handler(self, handler):
        self._log.error("gw_set_server_side_rpc_request_handler is not supported in AzGatewayDeviceClient")

    def set_server_side_rpc_request_handler(self, handler):
        self._log.error("set_server_side_rpc_request_handler is not supported in AzGatewayDeviceClient")

    def gw_subscribe_to_all_attributes(self, callback):
        self._log.error("gw_subscribe_to_all_attributes is not supported in AzGatewayDeviceClient")

    def subscribe_to_all_attributes(self, callback):
        self._log.error("subscribe_to_all_attributes is not supported in AzGatewayDeviceClient")

    def request_attributes(self, client_keys=None, shared_keys=None, callback=None):
        self._log.error("request_attributes is not supported in AzGatewayDeviceClient")



