#!/usr/bin/env python3
"""
Script para limpiar el estado de migraciones de colab y aplicar la migración citizens4water
"""

import os
import sys
import subprocess

def run_sql_command(sql_command):
    """Ejecutar comando SQL usando psql"""
    try:
        # Usar las variables de entorno de CKAN para conectarse
        env = os.environ.copy()
        
        # Ejecutar el comando SQL
        process = subprocess.run([
            'psql', 
            env.get('CKAN_SQLALCHEMY_URL', 'postgresql://ckan_default:password@postgres/ckan_default'),
            '-c', sql_command
        ], capture_output=True, text=True, env=env)
        
        if process.returncode == 0:
            print(f"✅ SQL ejecutado exitosamente: {sql_command[:50]}...")
            return True
        else:
            print(f"❌ Error ejecutando SQL: {process.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔧 Limpiando estado de migración de colab...")
    
    # Resetear la versión de Alembic a una versión estable
    print("🔄 Reseteando versión de Alembic...")
    
    sql_commands = [
        # Crear tabla si no existe
        """
        CREATE TABLE IF NOT EXISTS colab_alembic_version (
            version_num VARCHAR(32) NOT NULL PRIMARY KEY
        );
        """,
        
        # Insertar o actualizar versión
        """
        INSERT INTO colab_alembic_version (version_num) VALUES ('bc416bb48b61') 
        ON CONFLICT (version_num) DO UPDATE SET version_num = 'bc416bb48b61';
        """,
        
        # Verificar si la columna citizens4water existe
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'colab' AND column_name = 'citizens4water') THEN
                ALTER TABLE colab ADD COLUMN citizens4water VARCHAR;
                RAISE NOTICE 'Columna citizens4water agregada';
            ELSE
                RAISE NOTICE 'Columna citizens4water ya existe';
            END IF;
        END $$;
        """,
        
        # Crear tabla de organization_requests si no existe
        """
        CREATE TABLE IF NOT EXISTS colab_organization_requests (
            id SERIAL PRIMARY KEY,
            requester_username VARCHAR NOT NULL,
            organization_name VARCHAR NOT NULL,
            organization_description VARCHAR,
            organization_image_url VARCHAR,
            admin_username VARCHAR NOT NULL,
            organization_type VARCHAR,
            status VARCHAR DEFAULT 'pending',
            created_date TIMESTAMP,
            approved_by VARCHAR,
            approved_date TIMESTAMP,
            rejected_by VARCHAR,
            rejected_date TIMESTAMP,
            rejection_reason VARCHAR
        );
        """,
        
        # Actualizar versión a la nueva migración
        """
        UPDATE colab_alembic_version SET version_num = 'e8f9a0b1c2d4';
        """
    ]
    
    success = True
    for sql in sql_commands:
        if not run_sql_command(sql.strip()):
            success = False
            break
    
    if success:
        print("🎉 Estado de base de datos limpiado exitosamente")
        print("✅ Columna citizens4water disponible")
        print("✅ Tabla colab_organization_requests disponible")
        print("✅ Versión de Alembic actualizada")
    else:
        print("❌ Hubo errores durante la limpieza")
        print("\nInstrucciones manuales:")
        print("1. Conectar a PostgreSQL:")
        print("   psql $CKAN_SQLALCHEMY_URL")
        print("2. Ejecutar las siguientes consultas:")
        for sql in sql_commands:
            print(f"   {sql.strip()}")

if __name__ == "__main__":
    main()
