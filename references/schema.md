# travel-data.json

文字字段没查到填 `"未查到"` 或空；金额、评分和坐标等数值字段未知时填 `null`，不要用 `0` 冒充（金额 `0` 会显示为免费）。没有核实坐标的地点不要加入 `mapPoints`。不要编数据。`photoSpots.confidence` 固定 `"参考"`。`mapPoints.kind` 取值 `sight` | `food`。以下是字段结构模板，不是实际查询数据；完整离线示例见 [travel-data.example.json](../examples/travel-data.example.json)。

```json
{
  "meta": {
    "title": "",
    "origin": "",
    "destinations": [],
    "dateStart": "",
    "dateEnd": "",
    "days": 0,
    "people": 2,
    "currency": "CNY",
    "updatedAt": "",
    "note": "",
    "mapBoundary": ""
  },
  "flightsOrTrains": [
    {
      "mode": "flight|train",
      "from": "",
      "to": "",
      "date": "YYYY-MM-DD",
      "no": "",
      "depart": "HH:MM",
      "arrive": "HH:MM",
      "price": 0,
      "priceType": "实|估",
      "duration": "",
      "note": ""
    }
  ],
  "hotels": [
    {
      "date": "",
      "city": "",
      "name": "",
      "area": "",
      "price": 0,
      "priceType": "实|估",
      "score": "",
      "alt": "",
      "lockAdvice": ""
    }
  ],
  "days": [
    {
      "date": "YYYY-MM-DD",
      "city": "",
      "title": "",
      "am": "",
      "pm": "",
      "evening": "",
      "tickets": [{"name": "", "price": 0, "priceType": "实|估", "note": ""}],
      "warnings": [],
      "photoSpots": [
        {
          "name": "",
          "shot": "",
          "bestTime": "",
          "tip": "",
          "traffic": "",
          "source": "",
          "queriedAt": "",
          "confidence": "参考"
        }
      ],
      "foods": [
        {
          "name": "",
          "dish": "",
          "area": "",
          "avgPrice": 0,
          "priceType": "实|估",
          "score": 0,
          "openHours": "",
          "lat": 0,
          "lng": 0
        }
      ],
      "mapPoints": [
        {"name": "", "lat": 0, "lng": 0, "openHours": "", "kind": "sight|food"}
      ]
    }
  ],
  "todos": [{"text": "", "done": false, "priority": "P0|P1|P2"}],
  "budget": {
    "comfort": {"title": "", "items": {}, "total": 0, "perPerson": 0, "note": ""},
    "saver": {"title": "", "items": {}, "total": 0, "perPerson": 0, "note": ""}
  },
  "source": {
    "tripQueryAt": "",
    "mapQueryAt": "",
    "photoQueryAt": "",
    "notes": []
  }
}
```

隐私：护照、证件号、手机、邮箱、订单号、商户电话一律不进文件。
