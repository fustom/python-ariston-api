# python-ariston-api
A Python module for controlling Ariston devices with cloud polling.
The following devices are currently supported:
- Ariston Alteas One 24
- Ariston Velis Evo
- Ariston Lydos Hybrid
- Ariston Genus One

## Installation
Use pip3 to install the latest version of this module.
```
pip3 install ariston
```

## Basic functions
First, open Python 3 and import Ariston class from this module.
```
python3
```
```python3
from ariston import Ariston
```
Create a new Ariston instance
```python3
ariston = Ariston()
```
Now let's try some functions

## Connect
The cloud requests are asynchronous, so if you call them from a synchronous function or not even from function, you should use asyncio.
```python3
import asyncio
```

Sync
```python3
asyncio.run(ariston.async_connect("username", "password"))
```
Async
```python3
await ariston.async_connect("username", "password")
```
- username: Your ariston cloud username.
- password: Your ariston cloud password.

## Discovery
Use this function to discover devices. You can skip this step if you already know the gateway id.

Sync
```python3
devices = asyncio.run(ariston.async_discover())
```
Async
```python3
devices = await ariston.async_discover()
```

## Say hello
Use this function to create the device object.

Sync
```python3
device = asyncio.run(ariston.async_hello("gateway", is_metric, "location"))
```
Async
```python3
device = await ariston.async_hello("gateway", is_metric, "location")
```
- gateway: You can find the value in the returned discover dictionary name 'gw'
- is_metric: Optional. True or False. True means metric, False means imperial. Only works with Galevo (Alteas One, Genus One, etc) system. Default is True.
- language_tag: Optional. Check https://en.wikipedia.org/wiki/IETF_language_tag Only works with Galevo (Alteas One, Genus One, etc) system. Default is "en-US".
