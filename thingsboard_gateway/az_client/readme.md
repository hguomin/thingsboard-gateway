# Azure IoT Hub as upstream broker server for Thingsboard IoT gateway

With this branch source code and setup, you can ingest you device telemetry to Azure IoT Hub by leveraging the rich protocol support like `MQTT/Modbus/OPC-UA/BLE/CAN/BACnet/ODBC/REST/SNMP/FTP/Request` from Thingsboard IoT Gateway. 

This document desribes how to run Thingsboard IoT gateway together with Azure IoT Hub by leverage this integration support.  

## Create Azure IoT Hub and device identity 

We need a device identity with its SAS token to configure this gateway component to connect and send telmetry to Azure IoT Hub.  

1. Launch Azure CLI  
You can run [Azure Cloud Shell](https://shell.azure.com/bash) or Azure CLI locally to use the cli commands in below steps.  

2. Create Azure resource group
    
    ```bash
    az group create --name {Your Resource Group Name} --location {location, ex: eastasia}
    ```
3. Create an Azure IoT Hub in above resource group  
    ```bash
    az iot hub create --resource-group {Your Resource Group Name} --name {Your IoT Hub Name}
    ```
4. Create a device inside Azure IoT Hub
    ```bash
    az iot hub device-identity create --device-id {Your device id} --hub-name {Your IoT Hub Name}
    ```  
    Copy and note down the device id, you will need it later.

5. Generate a SAS token for the device 
    ```bash
    az iot hub generate-sas-token -d {Your device id} -n {Your IoT Hub Name}
    ```
    Copy and note down the SAS token, you will need it later
  

## Build Thingsboard Gateway from source code of this branch

1. Install required libraries 
    ```bash
    sudo apt install python3-dev python3-pip libglib2.0-dev git 
    ```
2. Clone the branch az/upstream-iothub
    ```bash
    git clone https://github.com/hguomin/thingsboard-gateway/tree/az/upstream-iothub
    ```
3. Build the code and install it as python module with the setup.py script
    ```bash
    cd thingsboard-gateway
    python setup.py develop
    ``` 
## Configure gateway to connect Azure IoT Hub as its upstream broker server  
Open the configuration file: `./thingsboard_gateway/config/tb_gateway.yaml`, set `upstream.server` to `azure` and use your iot hub name, device id and its sas token to configure `azure.iothub`, `azure.deviceId` and `azure.deviceSasToken`, see below configuration section:  
```yaml
upstream:
  server: azure

azure:
  iothub: PUT_YOUR_IOTHUB_NAME
  deviceId: PUT_YOUR_DEVICE_ID
  deviceSasToken: PUT_YOUR_DEVICE_SAS_TOKEN
  keep_alive: 120
```

Other configuration as well as connectors configuration is same as Thingsboard IoT Gateway's configuration, please follow [the offical guide](https://thingsboard.io/docs/iot-gateway/configuration/) to make it.  

## Debug or Run the gateway
Now you can start the debugging from the `tb_gateway.py` using your IDE like vscode, or just run the gateway and see the result with below command:
```bash
python ./thingsboard_gateway/tb_gateway.py
```
Enjoy it!
