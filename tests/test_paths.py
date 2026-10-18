import os
def test_ui_dirs_exist():
    from app.core.config import web,mobile
    assert os.path.isdir(web) and os.path.isfile(os.path.join(web,'index.html'))
    assert os.path.isdir(mobile) and os.path.isfile(os.path.join(mobile,'visitor','index.html'))
