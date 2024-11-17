import { createSlice } from '@reduxjs/toolkit';

export const optionsSlice = createSlice({
  name: 'options',
  initialState: {
    isOpen: false
  },
  reducers: {
    openOptions: state => {
      state.isOpen = true;
    }
  }
})

export const { openOptions } = optionsSlice.actions;
export default optionsSlice.reducer;