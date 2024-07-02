# Script para instalar pacotes R localmente

# Definir o diretório onde os pacotes serão instalados (local ao projeto Flask)
library_dir <- "./r_library"

# Verificar se o diretório existe, se não, criar
if (!dir.exists(library_dir)) {
  dir.create(library_dir, recursive = TRUE)
}

# Lista de pacotes a serem instalados
packages <- c("ggplot2", "rmarkdown", "jsonlite")

# Instalar pacotes
install.packages(packages, lib=library_dir, repos='http://cran.us.r-project.org')
