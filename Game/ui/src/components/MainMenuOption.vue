<template>
    <p 
      :class="['hover-underline-animation', colorClass]" 
      @click="handleClick">
      {{ text }}
    </p>
  </template>
  
  <script>
  export default {
    props: {
      text: {
        type: String,
        required: true
      },
      colorClass: {
        type: String,
        required: false,
        default: ''
      },
      onClick: {
        type: Function,
        required: true
      }
    },
    methods: {
      handleClick() {
        this.onClick();
      }
    }
  };
  </script>
  
  <style scoped>
  /* Additional classes for color */
  </style>
  