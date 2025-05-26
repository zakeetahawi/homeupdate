/**
 * Funcionalidad de arrastrar y soltar para la aplicación de inventario
 * Permite reordenar elementos en listas y mover productos entre categorías
 */

// Clase principal para la funcionalidad de arrastrar y soltar
class DragDropManager {
    constructor(options = {}) {
        // Opciones por defecto
        this.options = {
            draggableSelector: '.draggable',
            dropzoneSelector: '.dropzone',
            dragHandleSelector: '.drag-handle',
            dragActiveClass: 'dragging',
            dropzoneActiveClass: 'dropzone-active',
            dropzoneHoverClass: 'dropzone-hover',
            onDragStart: null,
            onDragEnd: null,
            onDrop: null,
            ...options
        };
        
        // Estado
        this.draggedElement = null;
        this.dropzones = [];
        
        // Inicializar
        this.init();
    }
    
    init() {
        // Obtener todos los elementos arrastrables
        const draggables = document.querySelectorAll(this.options.draggableSelector);
        
        // Configurar eventos para cada elemento arrastrable
        draggables.forEach(draggable => {
            // Configurar atributos
            draggable.setAttribute('draggable', 'true');
            
            // Eventos de arrastrar
            draggable.addEventListener('dragstart', this.handleDragStart.bind(this));
            draggable.addEventListener('dragend', this.handleDragEnd.bind(this));
            
            // Si hay un manejador de arrastre específico
            if (this.options.dragHandleSelector) {
                const handle = draggable.querySelector(this.options.dragHandleSelector);
                if (handle) {
                    handle.addEventListener('mousedown', () => {
                        draggable.setAttribute('draggable', 'true');
                    });
                    
                    handle.addEventListener('mouseup', () => {
                        draggable.setAttribute('draggable', 'false');
                    });
                }
            }
        });
        
        // Obtener todas las zonas de destino
        this.dropzones = document.querySelectorAll(this.options.dropzoneSelector);
        
        // Configurar eventos para cada zona de destino
        this.dropzones.forEach(dropzone => {
            dropzone.addEventListener('dragover', this.handleDragOver.bind(this));
            dropzone.addEventListener('dragenter', this.handleDragEnter.bind(this));
            dropzone.addEventListener('dragleave', this.handleDragLeave.bind(this));
            dropzone.addEventListener('drop', this.handleDrop.bind(this));
        });
    }
    
    handleDragStart(event) {
        // Guardar referencia al elemento arrastrado
        this.draggedElement = event.target;
        
        // Agregar clase de arrastre activo
        this.draggedElement.classList.add(this.options.dragActiveClass);
        
        // Configurar datos de transferencia
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', this.draggedElement.id);
        
        // Si hay una imagen de arrastre personalizada
        if (this.draggedElement.dataset.dragImage) {
            const img = new Image();
            img.src = this.draggedElement.dataset.dragImage;
            event.dataTransfer.setDragImage(img, 0, 0);
        }
        
        // Activar todas las zonas de destino
        this.dropzones.forEach(dropzone => {
            dropzone.classList.add(this.options.dropzoneActiveClass);
        });
        
        // Llamar al callback onDragStart si existe
        if (typeof this.options.onDragStart === 'function') {
            this.options.onDragStart(this.draggedElement);
        }
    }
    
    handleDragEnd(event) {
        // Eliminar clase de arrastre activo
        this.draggedElement.classList.remove(this.options.dragActiveClass);
        
        // Desactivar todas las zonas de destino
        this.dropzones.forEach(dropzone => {
            dropzone.classList.remove(this.options.dropzoneActiveClass);
            dropzone.classList.remove(this.options.dropzoneHoverClass);
        });
        
        // Llamar al callback onDragEnd si existe
        if (typeof this.options.onDragEnd === 'function') {
            this.options.onDragEnd(this.draggedElement);
        }
        
        // Limpiar referencia
        this.draggedElement = null;
    }
    
    handleDragOver(event) {
        // Prevenir el comportamiento por defecto para permitir soltar
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }
    
    handleDragEnter(event) {
        // Agregar clase de hover a la zona de destino
        event.target.classList.add(this.options.dropzoneHoverClass);
    }
    
    handleDragLeave(event) {
        // Eliminar clase de hover de la zona de destino
        event.target.classList.remove(this.options.dropzoneHoverClass);
    }
    
    handleDrop(event) {
        // Prevenir el comportamiento por defecto
        event.preventDefault();
        
        // Obtener la zona de destino
        const dropzone = event.target.closest(this.options.dropzoneSelector);
        
        // Eliminar clase de hover
        dropzone.classList.remove(this.options.dropzoneHoverClass);
        
        // Verificar que tenemos un elemento arrastrado y una zona de destino
        if (!this.draggedElement || !dropzone) return;
        
        // Llamar al callback onDrop si existe
        if (typeof this.options.onDrop === 'function') {
            this.options.onDrop(this.draggedElement, dropzone, event);
        } else {
            // Comportamiento por defecto: mover el elemento a la zona de destino
            dropzone.appendChild(this.draggedElement);
        }
    }
}

// Clase para reordenar elementos en una lista
class SortableList {
    constructor(listElement, options = {}) {
        this.listElement = typeof listElement === 'string' 
            ? document.querySelector(listElement) 
            : listElement;
        
        if (!this.listElement) {
            console.error('No se encontró el elemento de lista');
            return;
        }
        
        // Opciones por defecto
        this.options = {
            itemSelector: 'li',
            handleSelector: null,
            animation: true,
            animationDuration: 150,
            onSort: null,
            ...options
        };
        
        // Inicializar
        this.init();
    }
    
    init() {
        // Configurar el contenedor como una zona de destino
        this.listElement.classList.add('dropzone');
        
        // Configurar cada elemento de la lista como arrastrable
        const items = this.listElement.querySelectorAll(this.options.itemSelector);
        items.forEach(item => {
            item.classList.add('draggable');
            
            // Si hay un manejador específico
            if (this.options.handleSelector) {
                const handle = item.querySelector(this.options.handleSelector);
                if (handle) {
                    handle.classList.add('drag-handle');
                }
            }
        });
        
        // Inicializar el gestor de arrastrar y soltar
        this.dragDropManager = new DragDropManager({
            draggableSelector: `${this.options.itemSelector}.draggable`,
            dropzoneSelector: '.dropzone',
            dragHandleSelector: this.options.handleSelector ? '.drag-handle' : null,
            onDrop: this.handleSort.bind(this)
        });
    }
    
    handleSort(draggedElement, dropzone, event) {
        // Verificar que estamos en la misma lista
        if (dropzone !== this.listElement && !dropzone.closest(this.listElement)) {
            return;
        }
        
        // Encontrar el elemento sobre el que se está soltando
        const items = Array.from(this.listElement.querySelectorAll(this.options.itemSelector));
        const targetIndex = items.findIndex(item => {
            const rect = item.getBoundingClientRect();
            return event.clientY < rect.top + rect.height / 2;
        });
        
        // Si no se encontró un objetivo, agregar al final
        if (targetIndex === -1) {
            this.listElement.appendChild(draggedElement);
        } else {
            // Insertar antes del elemento objetivo
            this.listElement.insertBefore(draggedElement, items[targetIndex]);
        }
        
        // Animar el movimiento si está habilitado
        if (this.options.animation) {
            draggedElement.style.transition = `transform ${this.options.animationDuration}ms ease`;
            draggedElement.style.transform = 'scale(1.05)';
            
            setTimeout(() => {
                draggedElement.style.transform = 'scale(1)';
                
                setTimeout(() => {
                    draggedElement.style.transition = '';
                }, this.options.animationDuration);
            }, 0);
        }
        
        // Llamar al callback onSort si existe
        if (typeof this.options.onSort === 'function') {
            const newOrder = Array.from(this.listElement.querySelectorAll(this.options.itemSelector))
                .map(item => item.dataset.id || item.id);
            
            this.options.onSort(newOrder, draggedElement);
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Buscar listas ordenables
    const sortableLists = document.querySelectorAll('.sortable-list');
    
    // Inicializar cada lista
    sortableLists.forEach(list => {
        new SortableList(list, {
            itemSelector: '.sortable-item',
            handleSelector: '.sortable-handle',
            onSort: function(newOrder, draggedElement) {
                console.log('Nuevo orden:', newOrder);
                
                // Aquí se podría enviar el nuevo orden al servidor
                // mediante una petición AJAX
            }
        });
    });
});
