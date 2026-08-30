# API schema returned from a Tessera SX40 v3.5.2
### Querying a processor with the ```override?help=1``` flag returns a handy, human readable, schema for reference.

```bash
curl -s 'http://172.17.90.81/api/override?help=1' | jq .
```
```json
{
  "override": {
    "blackout": {
      "enabled": {
        "Access Specifier": "R/W",
        "Details": "Enables or disables blackout",
        "Name": "Blackout Enabled",
        "Summary": "Enable blackout",
        "Type": "Boolean"
      },
      "fade-time": {
        "Access Specifier": "R/W",
        "Details": "The value of the blackout fade time. The fade time may be adjusted between zero (snap) and 10 seconds",
        "Name": "Blackout Fade Time",
        "Summary": "Time taken to fade to black when blackout enabled",
        "Type": "Float (range: 0 - 10)"
      }
    },
    "freeze": {
      "enabled": {
        "Access Specifier": "R/W",
        "Details": "Enables or disables video freeze",
        "Name": "Freeze Enabled",
        "Summary": "Enable video freeze",
        "Type": "Boolean"
      }
    },
    "test-pattern": {
      "custom-colour": {
        "blue": {
          "Access Specifier": "R/W",
          "Details": "Gets or sets the custom colour test pattern blue value",
          "Name": "Test Pattern Custom Colour Blue",
          "Summary": "Custom colour test pattern blue value",
          "Type": "Integer (range: 0 - 4095)"
        },
        "green": {
          "Access Specifier": "R/W",
          "Details": "Gets or sets the custom colour test pattern green value",
          "Name": "Test Pattern Custom Colour Green",
          "Summary": "Custom colour test pattern green value",
          "Type": "Integer (range: 0 - 4095)"
        },
        "red": {
          "Access Specifier": "R/W",
          "Details": "Gets or sets the custom colour test pattern red value",
          "Name": "Test Pattern Custom Colour Red",
          "Summary": "Custom colour test pattern red value",
          "Type": "Integer (range: 0 - 4095)"
        }
      },
      "custom-gradient": {
        "end-colour": {
          "blue": {
            "Access Specifier": "R/W",
            "Details": "Gets or sets blue component of custom gradient test pattern end colour as a 12 bit integer",
            "Name": "Test Pattern Custom Gradient End Blue",
            "Summary": "Custom gradient test pattern end colour blue component",
            "Type": "Integer (range: 0 - 4095)"
          },
          "green": {
            "Access Specifier": "R/W",
            "Details": "Gets or sets green component of custom gradient test pattern end colour as a 12 bit integer",
            "Name": "Test Pattern Custom Gradient End Green",
            "Summary": "Custom gradient test pattern end colour green component",
            "Type": "Integer (range: 0 - 4095)"
          },
          "red": {
            "Access Specifier": "R/W",
            "Details": "Gets or sets red component of custom gradient test pattern end colour as a 12 bit integer",
            "Name": "Test Pattern Custom Gradient End Red",
            "Summary": "Custom gradient test pattern end colour red component",
            "Type": "Integer (range: 0 - 4095)"
          }
        },
        "orientation": {
          "Access Specifier": "R/W",
          "Details": "Gets or sets the custom gradient test pattern orientation",
          "Name": "Test Pattern Custom Gradient Orientation",
          "Summary": "Custom gradient test pattern orientation",
          "Type": "Enum (allowed values: horizontal,vertical)"
        },
        "start-colour": {
          "blue": {
            "Access Specifier": "R/W",
            "Details": "Gets or sets green component of custom gradient test pattern start colour as a 12 bit integer",
            "Name": "Test Pattern Custom Gradient Start Green",
            "Summary": "Custom gradient test pattern start colour green component",
            "Type": "Integer (range: 0 - 4095)"
          },
          "green": {
            "Access Specifier": "R/W",
            "Details": "Gets or sets blue component of custom gradient test pattern start colour as a 12 bit integer",
            "Name": "Test Pattern Custom Gradient Start Blue",
            "Summary": "Custom gradient test pattern start colour blue component",
            "Type": "Integer (range: 0 - 4095)"
          },
          "red": {
            "Access Specifier": "R/W",
            "Details": "Gets or sets red component of custom gradient test pattern start colour as a 12 bit integer",
            "Name": "Test Pattern Custom Gradient Start Red",
            "Summary": "Custom gradient test pattern start colour red component",
            "Type": "Integer (range: 0 - 4095)"
          }
        }
      },
      "enabled": {
        "Access Specifier": "R/W",
        "Details": "Enables or disables test pattern output function",
        "Name": "Test Pattern Enabled",
        "Summary": "Enable test pattern output function",
        "Type": "Boolean"
      },
      "format": {
        "Access Specifier": "R/W",
        "Details": "Format of the generated test pattern",
        "Name": "Test Pattern Format",
        "Summary": "Format of the generated test pattern",
        "Type": "Enum (allowed values: from-input,standard-dynamic-range,perceptual-quantiser,hybrid-log-gamma)"
      },
      "frame-store": {
        "capture-frame": {
          "Access Specifier": "W/O",
          "Details": "Captures the current frame and saves it to the frame store with the user number provided. (Warning: Specifying a user number that already exists will overwrite the existing frame. This operation cannot be undone.)",
          "Name": "Capture Frame",
          "Summary": "Capture a Frame from current video",
          "Type": "Integer (range: 1 - 50)"
        },
        "delete-frame": {
          "Access Specifier": "W/O",
          "Details": "Delete the frame store frame at the user number provided.",
          "Name": "Delete Frame",
          "Summary": "Delete a Frame Store frame",
          "Type": "Integer (range: 1 - 50)"
        },
        "frames": {
          "{frame-user-number}": {
            "colour-space": {
              "Access Specifier": "W/O",
              "Details": "Set colour space for the frame",
              "Name": "Frame Store Colour Space",
              "Summary": "Set colour space for the frame",
              "Type": "Enum (allowed values: rec-2020,dci-p3,rec-709,aces-cg,custom)"
            },
            "enable-alpha": {
              "Access Specifier": "R/W",
              "Details": "Set alpha mode for the frame",
              "Name": "Frame Store Alpha Enabled",
              "Summary": "Set alpha mode for the frame",
              "Type": "Boolean"
            },
            "format": {
              "Access Specifier": "W/O",
              "Details": "Set format for the frame",
              "Name": "Frame Store Format",
              "Summary": "Set format for the frame",
              "Type": "Enum (allowed values: from-input,standard-dynamic-range,perceptual-quantiser,hybrid-log-gamma)"
            },
            "name": {
              "Access Specifier": "R/W",
              "Details": "Name of the Frame",
              "Name": "Frame Name",
              "Summary": "Name of the Frame",
              "Type": "String"
            },
            "scaling-mode": {
              "Access Specifier": "W/O",
              "Details": "Set scaling mode for the frame",
              "Name": "Frame Store Scaling Mode",
              "Summary": "Set scaling mode for the frame",
              "Type": "Enum (allowed values: 1:1,stretch,fit,fill)"
            }
          }
        }
      },
      "restrict-to-achievable-colours": {
        "Access Specifier": "R/W",
        "Details": "Enables or disables restrict to achievable colours switch",
        "Name": "Test Pattern Restrict To Achievable Colours",
        "Summary": "Enables restrict to achievable colours switch",
        "Type": "Boolean"
      },
      "type": {
        "Access Specifier": "R/W",
        "Details": "Determines which test pattern or frame store image will be shown when the test pattern widget is activated. Accepts either a frame store user number, or test pattern title. Defaults to SMPTE bars.",
        "Name": "Test Pattern Type",
        "Summary": "Type of test pattern or frame store image to set as active.",
        "Type": "TestPatternType (allowed values: brompton,red,green,blue,cyan,magenta,yellow,white,black,grid,scrolling-grid,checkerboard,scrolling-checkerboard,colour-bars,scrolling-colour-bars,gradient,scrolling-gradient,strobe,smpte-bars,scrolling-smpte-bars,custom-colour,custom,forty-five-degree-grid,scrolling-forty-five-degree-grid,custom-gradient,scrolling-custom-gradient) (range: 1 - 50)"
      }
    }
  }
}
```
