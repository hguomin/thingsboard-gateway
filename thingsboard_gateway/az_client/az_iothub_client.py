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

import time
import threading
import logging
from os import path

from thingsboard_gateway.az_client.az_gateway_device_client import AzGatewayDeviceClient

log = logging.getLogger("tb_connection")


class AzIoTHubClient(threading.Thread):
    def __init__(self, config, config_folder_path):
        super().__init__()
        self.setName('Connection thread.')
        self.daemon = True
        self._config = config
        self.client = AzGatewayDeviceClient(config["iothub"] + ".azure-devices.net", config["deviceId"], config["deviceSasToken"], config_folder_path + "certs/azure/iothub_ca.cer".replace("/", path.sep), self._on_connect, self._on_disconnect)
 
        self._min_reconnect_delay = 1
        self._is_connected = False
        self._stopped = False
        self._paused = False
        
        self.start()


    def pause(self):
        self._paused = True

    def unpause(self):
        self._paused = False

    def is_connected(self):
        return self._is_connected

    def _on_connect(self, client, userdata, flags, result_code, *extra_params):
        log.info('AzIoTHubClient %s connected to IoT Hub', str(client))
        if result_code == 0:
            self._is_connected = True


    def _on_disconnect(self, client, userdata, result_code):
        log.info('AzIoTHubClient %s disconnected to IoT Hub', str(client))
        # pylint: disable=protected-access
        if self.client._client != client:
            log.info("AzIoTHubClient %s has been disconnected. Current client for connection is: %s", str(client), str(self.client._client))
            client.disconnect()
            client.loop_stop()
        else:
            self._is_connected = False

    def stop(self):
        self.client.disconnect()
        self._stopped = True

    def disconnect(self):
        self._paused = True
        self.unsubscribe('*')
        self.client.disconnect()

    def unsubscribe(self, subsription_id):
        pass
        #self.client.gw_unsubscribe(subsription_id)
        #self.client.unsubscribe_from_attribute(subsription_id)

    def connect(self, min_reconnect_delay=10):
        self._paused = False
        self._stopped = False
        self._min_reconnect_delay = min_reconnect_delay

    def run(self):
        keep_alive = self._config.get("keep_alive", 120)
        try:
            while not self.client.is_connected() and not self._stopped:
                if not self._paused:
                    if self._stopped:
                        break
                    log.debug("connecting to ThingsBoard")
                    try:
                        self.client.connect(keepalive=keep_alive,
                                            min_reconnect_delay=self._min_reconnect_delay)
                        pass
                    except ConnectionRefusedError:
                        pass
                    except Exception as e:
                        log.exception(e)
                time.sleep(1)
        except Exception as e:
            log.exception(e)
            time.sleep(10)

        while not self._stopped:
            try:
                if not self._stopped:
                    time.sleep(.1)
                else:
                    break
            except KeyboardInterrupt:
                self._stopped = True
            except Exception as e:
                log.exception(e)

