from flask import Flask, render_template, request, redirect, url_for, flash
from config import get_connection
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'logistica_almacen_secret_2024'  # Cambia esto en producción


# ──────────────────────────────────────────────
#  RUTA PRINCIPAL
# ──────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ──────────────────────────────────────────────
#  REGISTRAR EMPLEADO
# ──────────────────────────────────────────────
@app.route('/subir_empleado', methods=['GET', 'POST'])
def subir_empleado():
    if request.method == 'POST':
        # Datos del formulario
        nombre1   = request.form.get('nombre1', '').strip()
        nombre2   = request.form.get('nombre2', '').strip() or None
        apellido1 = request.form.get('apellido1', '').strip()
        apellido2 = request.form.get('apellido2', '').strip() or None
        password  = request.form.get('pass', '').strip()
        rol       = request.form.get('rol')
        estado    = request.form.get('estado')
        nss       = request.form.get('nss')
        sueldo    = request.form.get('sueldo')
        seccion   = request.form.get('seccion', '').strip()

        # Validaciones básicas
        if not all([nombre1, apellido1, password, rol, estado, nss, sueldo, seccion]):
            flash('Por favor, completa todos los campos obligatorios.', 'danger')
            return render_template('subir_empleado.html')

        # Valores automáticos del backend
        fecha_ingreso_ET   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        paquete_asignado_id = 0
        eliminado          = 0

        # OPCIÓN A (recomendada): hash SHA-256 — requiere VARCHAR(64) en columna `pass`
        # ALTER TABLE empleados CHANGE `pass` `pass` VARCHAR(64) NOT NULL;
        # OPCIÓN B: sin hash, para VARCHAR(25) — comenta la línea de abajo y descomenta la siguiente
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        # pass_hash = password  # <- Opción B: sin hash

        connection = get_connection()
        if connection is None:
            flash('Error de conexión con la base de datos.', 'danger')
            return render_template('subir_empleado.html')

        try:
            cursor = connection.cursor()
            sql = """
                INSERT INTO empleados
                    (nombre1, nombre2, apellido1, apellido2, pass, rol, estado,
                     paquete_asignado_id, nss, fecha_ingreso_ET, sueldo, seccion, eliminado)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            valores = (
                nombre1, nombre2, apellido1, apellido2, pass_hash,
                int(rol), int(estado), paquete_asignado_id,
                int(nss), fecha_ingreso_ET, int(sueldo), seccion, eliminado
            )
            cursor.execute(sql, valores)
            connection.commit()
            flash(f'Empleado "{nombre1} {apellido1}" registrado exitosamente.', 'success')
            return redirect(url_for('ver_tabla'))
        except Exception as e:
            connection.rollback()
            flash(f'Error al registrar empleado: {str(e)}', 'danger')
            return render_template('subir_empleado.html')
        finally:
            cursor.close()
            connection.close()

    return render_template('subir_empleado.html') 


# ──────────────────────────────────────────────
#  VER TABLA DE EMPLEADOS
# ──────────────────────────────────────────────
@app.route('/ver_tabla')
def ver_tabla():
    connection = get_connection()
    if connection is None:
        flash('Error de conexión con la base de datos.', 'danger')
        return render_template('ver_tabla.html', empleados=[])

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT empleado_id, nombre1, nombre2, apellido1, apellido2,
                   rol, estado, nss, fecha_ingreso_ET, sueldo, seccion,
                   paquete_asignado_id
            FROM empleados
            WHERE eliminado = 0
            ORDER BY empleado_id DESC
        """)
        empleados = cursor.fetchall()
        return render_template('ver_tabla.html', empleados=empleados)
    except Exception as e:
        print(f'[ERROR ver_tabla] {str(e)}')
        flash(f'Error al obtener empleados: {str(e)}', 'danger')
        return render_template('ver_tabla.html', empleados=[])
    finally:
        cursor.close()
        connection.close()


# ──────────────────────────────────────────────
#  ELIMINAR EMPLEADO (soft delete)
# ──────────────────────────────────────────────
@app.route('/eliminar_empleado/<int:empleado_id>', methods=['POST'])
def eliminar_empleado(empleado_id):
    connection = get_connection()
    if connection is None:
        flash('Error de conexión con la base de datos.', 'danger')
        return redirect(url_for('ver_tabla'))

    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE empleados SET eliminado = 1 WHERE empleado_id = %s",
            (empleado_id,)
        )
        connection.commit()
        flash('Empleado eliminado correctamente.', 'success')
    except Exception as e:
        connection.rollback()
        flash(f'Error al eliminar empleado: {str(e)}', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('ver_tabla'))


if __name__ == '__main__':
    app.run(debug=True)
