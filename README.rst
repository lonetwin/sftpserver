sftpserver
==========

``sftpserver`` is a skeletal SFTP server written using `Paramiko`_

This project exists to serve as a starting point / demonstration of how to build
an SFTP server or as something to be used in tests. As such the goal is *not* to
provide a full featured sftp server.

This was initially a simple fork of `@rspivak`'s `sftpserver`_, which in turn
was an adaptation of the code from Paramiko's tests. However, I updated it
further to demonstrate the use of different `threaded` and `forked` modes of
operation.


Examples
--------

::

    # run sftpserver with defaults (serving current dir, at
    # localhost:3373, in threaded mode)

    $ python -m sftpserver

    # run sftpserver with defaults (serving dir /tmp, at
    # localhost:3373, in forked mode, using server key /tmp/test_rsa.key)

    $ sftpserver -r /tmp -k /tmp/test_rsa.key -l DEBUG -m forked


Generating a test private key::

    $ openssl req -out CSR.csr -new -newkey rsa:2048 -nodes -keyout /tmp/test_rsa.key

Connecting with a Python client to our server::

    >>> import paramiko
    >>> pkey = paramiko.RSAKey.from_private_key_file('/tmp/test_rsa.key')
    >>> transport = paramiko.Transport(('localhost', 3373))
    >>> transport.connect(username='admin', password='admin', pkey=pkey)
    >>> sftp = paramiko.SFTPClient.from_transport(transport)
    >>> sftp.listdir('.')
    ['loop.py', 'stub_sftp.py']


.. _Paramiko: https://www.paramiko.org/
.. _sftpserver: https://github.com/rspivak/sftpserver
