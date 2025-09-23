from car import Car

def test_car_defaults_are_reasonable():
    c = Car([0, 0], 0, 20, False, [], [], 0, 0)
    assert isinstance(c.radars, list)
    assert isinstance(c.speed, (int, float))