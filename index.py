import logging
import log_config as log_config

if __name__ == '__main__':
    from main import main
    log_config.setup()
    logger = logging.getLogger(__name__)
    logger.info('BoringXplorer logger initialized')
    main()