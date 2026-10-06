cases = [
    {
        "expr": "> 8 & <= 9 | > 14 & < 20",
        "value_table": {
            10: False,
            9: True, 
            14: False,
            15: True,
            19: True,
            21: False
        }
    },
    {
        "expr": " > 120 & (< 150 | > 230)",
        "value_table": {
            0: False,
            100: False,
            120: False,
            125: True,
            145: True,
            150: False, 
            200: False,
            230: False,
            250: True
        }
    },
    {
        "expr": "(> 10 & (< 80 & > 20) )",
        "value_table": {
            10: False,
            20: False,
            30: True, 
            70: True,
            80: False
        }
    }, {
        "expr": "(> 2) and <5",
        "value_table": {
            2: False,
            3: True,
            4: True,
            5: False
        }
    }, {
        "expr": "(((>0)))",
        "value_table": {
            2: True,
            1: True,
            0: False,
            -1: False,
            -2: False
        }
    }
]