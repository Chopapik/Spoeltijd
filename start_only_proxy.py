from core import Bridge

def main():
    print("Starting proxy only (no app/panel)...")
    bridge = Bridge(2002)
    bridge.start_server()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nProxy stopped.")

if __name__ == "__main__":
    main()