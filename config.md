{
    "buttons": {
        "type": "array",
        "description": "List of saved custom toolbar buttons (automatically maintained by the add-on UI)",
        "items": {
            "type": "object",
            "properties": {
                "icon":     { "type": "string",  "description": "Button icon, text, or Emoji" },
                "shortcut": { "type": "string",  "description": "Shortcut key combination, e.g., Ctrl+Shift+B, F8 (leave empty for none)" },
                "type":     { "type": "integer", "description": "1=Insert content, 2=Wrap selected text" },
                "content":  { "type": "string",  "description": "Type 1: Content to insert" },
                "left":     { "type": "string",  "description": "Type 2: Left content" },
                "right":    { "type": "string",  "description": "Type 2: Right content" }
            }
        }
    }
}
