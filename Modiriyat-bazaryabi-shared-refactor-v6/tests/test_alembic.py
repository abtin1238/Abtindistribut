import os,pytest
pytest.importorskip('alembic')
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/abtin_dist_alembic_app.sqlite3')
os.environ.setdefault('ADMIN_PASSWORD','test-password')
def test_upgrade_head_on_empty_db(tmp_path):
 from alembic.config import Config
 from alembic import command
 from sqlalchemy import create_engine,inspect
 url='sqlite:///'+str(tmp_path/'m.sqlite3');cfg=Config(os.path.join(os.path.dirname(os.path.dirname(__file__)),'alembic.ini'));cfg.set_main_option('sqlalchemy.url',url)
 cfg.set_main_option('script_location',os.path.join(os.path.dirname(os.path.dirname(__file__)),'migrations'))
 command.upgrade(cfg,'head');names=set(inspect(create_engine(url)).get_table_names())
 assert {'journal_lines','accounts','sales_returns','invoices','gps_points','alembic_version'}<=names
 command.upgrade(cfg,'head')
