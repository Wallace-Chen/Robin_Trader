import logging 
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] - %(message)s',
    filename='log/tmp.txt')  # pass explicit filename here 
logger = logging.getLogger()  # get the root logger
logger.warning('This should go in the file.')
#print logger.handlers   # you should have one FileHandler object
