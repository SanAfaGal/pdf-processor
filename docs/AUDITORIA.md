# Reporte de Auditoría: Hallazgos en la Indexación Documental

## 1. Errores de Tipificación (Prefijos)
- **Uso incorrecto de PDX:** Se están marcando las **Autorizaciones** como `PDX`, cuando el prefijo correcto es **`PDE`**. (Este es el error más recurrente).
- **Confusión en Electrocardiogramas:** Se están guardando los electros bajo el prefijo `HEV` en lugar de **`PDX`**.
- **Error en Autorizaciones:** Se está utilizando el prefijo `OPF` para documentos que corresponden a una autorización (**`PDE`**).
- **Mal uso de OPF:** Se le asigna el prefijo `PDX` a documentos que deberían ser clasificados como **`OPF`**.
- **Soportes de ADRES:** Se está guardando el ADRES como `PDE` cuando no existe una autorización física, sino que son solo soportes.

## 2. Calidad de la Información y Datos
- **Errores de NIT:** Inconsistencias y errores de digitación en los números de **NIT**.
- **Facturas sin CUFE:** Se han detectado facturas guardadas que carecen del código **CUFE**, imposibilitando su validación legal.

## 3. Integridad del Archivo
- **Archivos Fusionados:** Se están guardando **Resultados (PDX)** dentro del mismo archivo PDF de la **Historia Clínica**, dificultando la consulta individual de los mismos.

## 4. Gestión de Estructura y Carpetas
- **Carpetas Pendientes:** Omisión en el renombrado de carpetas, lo que deja el proceso con apariencia de “pendiente” o “inconcluso” en el sistema.