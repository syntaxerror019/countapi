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

## Notes & Best Practices

- Use unique keys.... all counters are public.
- Keys do not expire. If you need a “reset,” just create a new key.
- There is no guaranteed SLA, but the service is generally online 24/7.

---

## Learn More

For full documentation, endpoints, and more, check out 
https://countapi.mileshilliard.com

Or reach out directly via email: miles@mileshilliard.com
