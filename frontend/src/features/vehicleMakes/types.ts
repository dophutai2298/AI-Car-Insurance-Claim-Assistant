export type VehicleManufacturer = {
  id: number;
  name: string;
  is_active: boolean;
};

export type VehicleManufacturerWrite = {
  name: string;
};

export type VehicleManufacturerUpdate = VehicleManufacturerWrite & {
  is_active: boolean;
};
