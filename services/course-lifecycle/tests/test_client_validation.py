import pytest
from app.contracts import ClientCourse, CourseIdentity, CourseOutcome, Module, ModuleOutcome, TimeDistribution, Credits

def test_valid_client_course():
    data = {
        "course_identity": {
            "program": "B.Tech",
            "course_code": "CS101",
            "course_title": "Intro to CS",
            "credits": {"l": 3, "t": 1, "p": 0, "total": 4}
        },
        "pos": ["PO1", "PO2", "PO3", "PO4", "PO5", "PO6", "PO7", "PO8", "PO9", "PO10", "PO11", "PO12"],
        "cos": [
            {"id": "CO1", "description": "Desc 1", "bloom_level": "Understand"},
            {"id": "CO2", "description": "Desc 2", "bloom_level": "Apply"},
            {"id": "CO3", "description": "Desc 3", "bloom_level": "Analyze"},
            {"id": "CO4", "description": "Desc 4", "bloom_level": "Evaluate"}
        ],
        "co_po_map": [
            [3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0]
        ],
        "modules": [
            {
                "id": "M1",
                "title": "Module 1",
                "mos": [
                    {"id": "MO1", "title": "MO1", "topics": ["T1", "T2"]}
                ],
                "mo_co_map": [
                    [3, 0, 0, 0] # 1 MO x 4 COs
                ]
            }
        ],
        "time_distribution": {
            "module_weights": [1.0] # 1 Module, total 1.0
        }
    }
    course = ClientCourse(**data)
    assert course.course_identity.course_code == "CS101"

def test_invalid_matrices():
    # Mismatch CO count and Matrix rows
    data = {
        "course_identity": {
            "program": "B.Tech",
            "course_code": "CS101",
            "course_title": "Intro to CS",
            "credits": {"l": 3, "t": 1, "p": 0, "total": 4}
        },
        "pos": ["PO1"] * 12,
        "cos": [
            {"id": "CO1", "description": "Desc 1", "bloom_level": "Understand"},
            {"id": "CO2", "description": "Desc 2", "bloom_level": "Apply"},
            {"id": "CO3", "description": "Desc 3", "bloom_level": "Analyze"},
            {"id": "CO4", "description": "Desc 4", "bloom_level": "Evaluate"}
        ],
        "co_po_map": [ # Only 3 rows, but 4 COs
            [3] * 12,
            [3] * 12,
            [3] * 12
        ],
        "modules": [],
        "time_distribution": {"module_weights": []}
    }
    with pytest.raises(ValueError, match="CO-PO matrix rows"):
        ClientCourse(**data)

def test_invalid_module_weights():
    with pytest.raises(ValueError, match="Module weights sum to 0.5"):
        TimeDistribution(module_weights=[0.5]) # Should be 1.0

def test_credits_validation():
    with pytest.raises(ValueError, match="Course must have at least some L/T/P hours"):
        Credits(l=0, t=0, p=0, total=1)
