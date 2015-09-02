
import sys
sys.path.insert(0, '/home/www/tile/thas')

import main
import user

application = main.application

if __name__ == "__main__":
    from pesto.testing import TestApp
    print(TestApp(application).get('/'))

