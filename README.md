# Flask Example

This project uses Flask.

## Setting the FLASK_APP environment variable

Set the `FLASK_APP` variable before running Flask commands:

- **Linux/Mac**:
  ```sh
  export FLASK_APP=main.py
  ```
- **Windows CMD**:
  ```cmd
  set FLASK_APP=main.py
  ```
- **PowerShell**:
  ```powershell
  $env:FLASK_APP = 'main.py'
  ```

## Activating the virtual environment

```sh
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate        # Windows
```

## Running the app

After activating the environment and setting `FLASK_APP`, run:

```sh
flask run
```

