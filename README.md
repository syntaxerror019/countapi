# CountAPI

A free, no-auth, no-rate-limit counting API for developers.

CountAPI is a lightweight spin-off inspired by the original countapi.xyz. It provides a simple way to track counters using unique keys — perfect for blogs, apps, scripts, or personal projects.

Key Features:

- No signup or API keys required
- Instant and unlimited usage
- Track counters globally
- Simple GET endpoints

Disclaimer: This service is not affiliated with countapi.xyz.

---

## How to Use

### Increment a counter
GET https://countapi.mileshilliard.com/api/v1/hit/your_key

Response:
```
{
  "key": "your_key",
  "message": "Key updated successfully",
  "value": 3
}
```

### Get current value
GET https://countapi.mileshilliard.com/api/v1/get/your_key

Response:
```
{
  "key": "your_key",
  "value": 3
}
```

### Set a counter
GET https://countapi.mileshilliard.com/api/v1/set/your_key?value=100

Response:
```
{
  "key": "your_key",
  "old_value": 3,
  "value": 100
}
```

---

## Javascript
```js
<script>
const BASE = "https://countapi.mileshilliard.com/api/v1";
const KEY = "my_counter";

// Increment
fetch(`${BASE}/hit/${KEY}`)
  .then(res => res.json())
  .then(data => console.log("Hit:", data));

// Get current value
fetch(`${BASE}/get/${KEY}`)
  .then(res => res.json())
  .then(data => console.log("Get:", data));

// Set counter
fetch(`${BASE}/set/${KEY}?value=100`)
  .then(res => res.json())
  .then(data => console.log("Set:", data));
</script>
```

## Command Line
```bash
# Increment a counter
curl https://countapi.mileshilliard.com/api/v1/hit/my_counter

# Get current value
curl https://countapi.mileshilliard.com/api/v1/get/my_counter

# Set a counter to a specific value
curl "https://countapi.mileshilliard.com/api/v1/set/my_counter?value=100"
```

## Python
```py
import requests

BASE = "https://countapi.mileshilliard.com/api/v1"
KEY = "my_counter"

# Increment counter
res = requests.get(f"{BASE}/hit/{KEY}")
print(res.json())

# Get current value
res = requests.get(f"{BASE}/get/{KEY}")
print(res.json())

# Set counter
res = requests.get(f"{BASE}/set/{KEY}?value=100")
print(res.json())
```

## Node.JS
```js
const fetch = require('node-fetch');
const BASE = "https://countapi.mileshilliard.com/api/v1";
const KEY = "my_counter";

// Increment counter
fetch(`${BASE}/hit/${KEY}`)
  .then(res => res.json())
  .then(console.log);

// Get current value
fetch(`${BASE}/get/${KEY}`)
  .then(res => res.json())
  .then(console.log);

// Set counter
fetch(`${BASE}/set/${KEY}?value=100`)
  .then(res => res.json())
  .then(console.log);
```

---

## Notes & Best Practices

- Use unique keys.... all counters are public.
- Keys do not expire. If you need a “reset,” just create a new key.
- There is no guaranteed SLA, but the service is generally online 24/7.

---

## Learn More

For full documentation, endpoints, and more, check out 
https://countapi.mileshilliard.com

Or reach out directly via email: miles@mileshilliard.com
