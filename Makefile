.PHONY: build install logs deploy build-tw

# Build, install and show logs
deploy: build-apk install logs

clean:
	rm -rf src/app/data/*
	rm -rf src/app/assets/*
	rm -rf src/app/index.html

# Clean bin directory and build APK
build-apk: clean build-tw  build-react
	rm -rf bin/*
	@echo "Building APK..."
	./remote-build

build-mac: clean build-tw build-react
	rm -rf dist/*
	@echo "Building for macOS..."
	python setup.py py2app 
	
# Install APK to connected device
install:
	@echo "Installing APK..."
	adb -s emulator-5556 install bin/*.apk

# Show Python logs from device
logs:
	@echo "Showing Python logs (Ctrl+C to stop)..."
	adb -s emulator-5556 logcat | grep -i python

build-tw:
	cd plugin && tiddlywiki \
		++./src/ \
		+plugins/tiddlywiki/tiddlyweb \
		+plugins/tiddlywiki/highlight \
		+themes/tiddlywiki/vanilla \
		+themes/tiddlywiki/snowwhite \
		--output ../src/app/data/ \
		--render "$$:/core/save/all" \
		base.html "text/plain"

build-react:
	cd react-app && npm run build

run: clean build-tw build-react
	python src/main.py