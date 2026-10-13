from tests._utils.spread import spread

cases = [
    *spread(("value", "result"),
        [
            (10, True),
            (5, True),
            (4, False),
            (1, False),
            (-5, False)
        ]
    ) * { "expr": "> 4" } 
]

