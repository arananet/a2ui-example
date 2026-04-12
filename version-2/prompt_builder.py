"""A2UI Prompt Builder for the Unsplash Photo Explorer Agent.

This module contains the photo gallery UI templates (A2UI JSON) and the logic to
inject UI-specific instructions and schemas into the agent's system prompt.

The agent uses the '---a2ui_JSON---' delimiter to separate conversational text
from structured A2UI payload in its responses.
"""

from a2ui_schema import A2UI_SCHEMA

# ------------------------------------------------------------------------------
# PHOTO GALLERY UI EXAMPLE
# This template demonstrates the expected A2UI output for a photo search result.
# It uses valueStruct (dataModelUpdate) to decouple data from component layout,
# enabling efficient updates without re-rendering the entire surface.
# ------------------------------------------------------------------------------

PHOTO_GALLERY_UI_EXAMPLE = """
---BEGIN PHOTO_GALLERY_EXAMPLE---
[
  {
    "beginRendering": {
      "surfaceId": "photo-surface",
      "root": "root",
      "styles": {
        "primaryColor": "#1565C0",
        "font": "Inter"
      }
    }
  },
  {
    "surfaceUpdate": {
      "surfaceId": "photo-surface",
      "components": [
        {
          "id": "root",
          "component": {
            "Card": {
              "child": "mainColumn"
            }
          }
        },
        {
          "id": "mainColumn",
          "component": {
            "Column": {
              "children": {
                "explicitList": [
                  "headerRow",
                  "statsRow",
                  "photoGrid",
                  "paginationRow"
                ]
              },
              "distribution": "start",
              "alignment": "center"
            }
          }
        },
        {
          "id": "headerRow",
          "component": {
            "Column": {
              "children": {
                "explicitList": [
                  "appTitle",
                  "searchQueryLabel"
                ]
              },
              "distribution": "start",
              "alignment": "center"
            }
          }
        },
        {
          "id": "appTitle",
          "component": {
            "Text": {
              "text": {
                "literalString": "Unsplash Photo Explorer"
              },
              "usageHint": "h1"
            }
          }
        },
        {
          "id": "searchQueryLabel",
          "component": {
            "Text": {
              "text": {
                "path": "/photos/query"
              },
              "usageHint": "h3"
            }
          }
        },
        {
          "id": "statsRow",
          "component": {
            "Row": {
              "children": {
                "explicitList": [
                  "totalResultsText",
                  "pageInfoText"
                ]
              },
              "distribution": "spaceBetween",
              "alignment": "center"
            }
          }
        },
        {
          "id": "totalResultsText",
          "component": {
            "Text": {
              "text": {
                "path": "/photos/totalLabel"
              },
              "usageHint": "caption"
            }
          }
        },
        {
          "id": "pageInfoText",
          "component": {
            "Text": {
              "text": {
                "path": "/photos/pageLabel"
              },
              "usageHint": "caption"
            }
          }
        },
        {
          "id": "photoGrid",
          "component": {
            "List": {
              "children": {
                "template": {
                  "componentId": "photoCard",
                  "dataBinding": "/photos/results"
                }
              },
              "direction": "horizontal",
              "wrap": true
            }
          }
        },
        {
          "id": "photoCard",
          "component": {
            "Card": {
              "child": "photoCardColumn"
            }
          }
        },
        {
          "id": "photoCardColumn",
          "component": {
            "Column": {
              "children": {
                "explicitList": [
                  "photoImage",
                  "photographerRow",
                  "photoDescription",
                  "tagsText",
                  "viewButton"
                ]
              },
              "distribution": "start",
              "alignment": "start"
            }
          }
        },
        {
          "id": "photoImage",
          "component": {
            "Image": {
              "url": {
                "path": "/photos/results[]/url"
              },
              "fit": "cover",
              "usageHint": "smallFeature"
            }
          }
        },
        {
          "id": "photographerRow",
          "component": {
            "Row": {
              "children": {
                "explicitList": [
                  "photographerLabel",
                  "photographerName"
                ]
              },
              "distribution": "start",
              "alignment": "center"
            }
          }
        },
        {
          "id": "photographerLabel",
          "component": {
            "Text": {
              "text": {
                "literalString": "Photo by "
              },
              "usageHint": "caption"
            }
          }
        },
        {
          "id": "photographerName",
          "component": {
            "Text": {
              "text": {
                "path": "/photos/results[]/photographerName"
              },
              "usageHint": "caption"
            }
          }
        },
        {
          "id": "photoDescription",
          "component": {
            "Text": {
              "text": {
                "path": "/photos/results[]/description"
              },
              "usageHint": "body"
            }
          }
        },
        {
          "id": "tagsText",
          "component": {
            "Text": {
              "text": {
                "path": "/photos/results[]/tags"
              },
              "usageHint": "caption"
            }
          }
        },
        {
          "id": "viewButton",
          "component": {
            "Button": {
              "label": {
                "literalString": "View on Unsplash"
              },
              "action": {
                "openUrl": {
                  "url": {
                    "path": "/photos/results[]/profileUrl"
                  }
                }
              }
            }
          }
        },
        {
          "id": "paginationRow",
          "component": {
            "Row": {
              "children": {
                "explicitList": [
                  "prevButton",
                  "nextButton"
                ]
              },
              "distribution": "center",
              "alignment": "center"
            }
          }
        },
        {
          "id": "prevButton",
          "component": {
            "Button": {
              "label": {
                "literalString": "Previous Page"
              },
              "action": {
                "sendMessage": {
                  "text": {
                    "path": "/photos/prevPagePrompt"
                  }
                }
              }
            }
          }
        },
        {
          "id": "nextButton",
          "component": {
            "Button": {
              "label": {
                "literalString": "Next Page"
              },
              "action": {
                "sendMessage": {
                  "text": {
                    "path": "/photos/nextPagePrompt"
                  }
                }
              }
            }
          }
        }
      ]
    }
  },
  {
    "dataModelUpdate": {
      "surfaceId": "photo-surface",
      "valueStruct": {
        "photos": {
          "query": "mountain landscape",
          "total": 1500,
          "totalLabel": "1,500 photos found",
          "totalPages": 167,
          "currentPage": 1,
          "pageLabel": "Page 1 of 167",
          "prevPagePrompt": "Show me page 0 of mountain landscape",
          "nextPagePrompt": "Show me page 2 of mountain landscape",
          "results": [
            {
              "id": "abc123",
              "url": "https://images.unsplash.com/photo-example-1?w=400",
              "photographerName": "John Doe",
              "description": "A stunning alpine meadow with snow-capped peaks",
              "profileUrl": "https://unsplash.com/@johndoe",
              "downloadUrl": "https://unsplash.com/photos/abc123/download",
              "tags": "mountain, landscape, nature, snow"
            },
            {
              "id": "def456",
              "url": "https://images.unsplash.com/photo-example-2?w=400",
              "photographerName": "Jane Smith",
              "description": "Golden hour light over rocky terrain",
              "profileUrl": "https://unsplash.com/@janesmith",
              "downloadUrl": "https://unsplash.com/photos/def456/download",
              "tags": "golden hour, rocks, sunset, light"
            }
          ]
        }
      }
    }
  }
]
---END PHOTO_GALLERY_EXAMPLE---
"""

# ------------------------------------------------------------------------------
# DYNAMIC THEMING RULES
# The agent selects a primaryColor based on the search topic category.
# ------------------------------------------------------------------------------

THEMING_RULES = """
## Dynamic Theming

Select `primaryColor` in `beginRendering.styles` based on the dominant theme of the search query:

| Topic Category                        | Primary Color | Hex       |
|---------------------------------------|--------------|-----------|
| nature / landscape / forest / ocean   | Teal         | #00897B   |
| architecture / city / urban / building| Indigo       | #3949AB   |
| food / drink / cooking / cuisine      | Amber        | #F57C00   |
| art / abstract / creative / design    | Purple       | #8E24AA   |
| sport / fitness / action / adventure  | Red          | #E53935   |
| people / portrait / face / culture    | Blue Grey    | #546E7A   |
| travel / road / explore / journey     | Teal         | #00897B   |
| technology / minimal / futuristic     | Cyan         | #00838F   |
| default (any other topic)             | Deep Blue    | #1565C0   |
"""

# ------------------------------------------------------------------------------
# FULL UI INSTRUCTION BUILDER
# ------------------------------------------------------------------------------

def get_ui_instruction(base_instructions: str) -> str:
    """Wraps base agent instructions with full A2UI schema, templates, and rules.

    This function constructs the complete system prompt by combining:
    - The agent's core persona/task instructions
    - The A2UI JSON Schema (for structural validation)
    - The photo gallery UI example (as a concrete rendering template)
    - Dynamic theming rules
    - Output format rules (delimiter, when to emit A2UI)

    Args:
        base_instructions: The agent's core persona and task description.

    Returns:
        The complete system prompt string with all A2UI guidance embedded.
    """
    return f"""
{base_instructions}

================================================================================
## A2UI RENDERING INSTRUCTIONS
================================================================================

You MUST produce A2UI output whenever you return photo search results.
A2UI output is a structured JSON payload that the client renders as a UI.

### Output Format

Your response MUST follow this exact structure when returning photo results:

    <your conversational message here>

    ---a2ui_JSON---
    <valid A2UI JSON array here>

The text BEFORE `---a2ui_JSON---` is displayed as a chat message.
The JSON AFTER the delimiter is parsed and rendered as a UI surface.

### When to Emit A2UI

- ALWAYS emit A2UI when you have photo search results to display.
- Do NOT emit A2UI for purely conversational responses (greetings, clarifications).
- Each search result response should emit a COMPLETE set of 3 messages:
  1. `beginRendering` — initialize the surface with theme color and font
  2. `surfaceUpdate` — define the component tree
  3. `dataModelUpdate` — populate the data via valueStruct

### A2UI JSON Schema

The following JSON Schema defines all valid A2UI message structures.
Your output MUST conform to this schema.

{A2UI_SCHEMA}

### Photo Gallery Template

Use this as the canonical template for rendering photo search results.
Adapt the `valueStruct` data to match actual API response values.

{PHOTO_GALLERY_UI_EXAMPLE}

{THEMING_RULES}

### Data Binding Rules

- Use `valueStruct` paths (e.g., `/photos/results[]/url`) to bind data to components.
- The `results` array in `valueStruct` contains one object per photo.
- Always populate: `query`, `totalLabel`, `pageLabel`, `prevPagePrompt`, `nextPagePrompt`.
- For each photo result: `id`, `url`, `photographerName`, `description`, `profileUrl`, `tags`.
- `url` should use the Unsplash `small` or `regular` size URL for display.
- `profileUrl` should link to the photographer's Unsplash profile page.

### Pagination

- Default page size is 9 photos (3×3 grid).
- `prevPagePrompt` and `nextPagePrompt` should be natural-language messages
  that the user can send to trigger navigation, e.g.:
  "Show me page 2 of mountain landscape photos"

### Attribution

Always include photographer attribution in the UI per Unsplash API guidelines.
The `photographerName` field and `profileUrl` button fulfill this requirement.
================================================================================
"""
