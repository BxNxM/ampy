## ampy2

An experimental flavour of the original micropython tool from adafruit.

### Why?

This project aims to rectify the inherent problems that `ampy` and the underlying `pyboard.py` face, due to lack of a _proper_ automate-able interface in micropython itself.

These tools end up simulating a human on the REPL, which is not very ideal. (See - [#64](https://github.com/pycampers/ampy/issues/64))

### Ideas

- [ ] Easy building and flashing frozen micropython firmware. 
    - [Dockerfile](https://github.com/micropython/micropython/pull/5003)
	- [firmware_builder.py](https://github.com/pycampers/ampy/blob/ampy2/ampy/firmware_builder.py)
- [ ] RPC interface that works transparently over both serial and WiFi.
- [ ] Faster development cycles, similar to flutter's hot restart.
- [ ] Collaborative environment hat allows N developers to work on M devices at the same time.
- [ ] Automate-able API that other toolchains and GUIs can exploit.
- [ ] A plugin system that allows 3rd parties to extend ampy's functionality. (Like [cargo plugins](https://lib.rs/development-tools/cargo-plugins))
- [ ] Install-able without a Python environment, by building distributable EXEs.

